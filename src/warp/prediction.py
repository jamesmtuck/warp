"""Next-command prediction based on sequential history patterns."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from warp.config import WarpConfig
from warp.db import get_command_sequences, get_connection, get_recent_commands, row_to_search_result
from warp.normalize import extract_verb, normalize_command
from warp.ranking import _parse_timestamp


@dataclass
class PredictedCommand:
    """A predicted next command candidate."""

    command: str
    score: float
    reasons: list[str] = field(default_factory=list)


# Maximum seconds between two commands to be considered a sequence
_MAX_SEQUENCE_GAP_SECS = 600  # 10 minutes


def _is_valid_sequence(
    prev_session: Optional[str],
    next_session: Optional[str],
    prev_ts: Optional[str],
    next_ts: Optional[str],
) -> bool:
    """Return True when two adjacent rows form a meaningful sequential pair."""
    # Same named session (not 'unknown') is always valid
    if (
        prev_session
        and next_session
        and prev_session != "unknown"
        and next_session != "unknown"
        and prev_session == next_session
    ):
        return True

    # Fall back to time-proximity check
    if prev_ts and next_ts:
        t_prev = _parse_timestamp(prev_ts)
        t_next = _parse_timestamp(next_ts)
        if t_prev and t_next:
            gap = (t_next - t_prev).total_seconds()
            return 0 <= gap <= _MAX_SEQUENCE_GAP_SECS

    return False


def _contextualize(command: str, old_cwd: str, new_cwd: str) -> str:
    """Replace *old_cwd* with *new_cwd* inside *command* when appropriate.

    Only substitutes when the paths differ and the old one actually appears
    as a token boundary so we don't corrupt partial matches.
    """
    if old_cwd and new_cwd and old_cwd != new_cwd and old_cwd in command:
        return command.replace(old_cwd, new_cwd)
    return command


def _recency_weight(timestamp: Optional[str], now: datetime) -> float:
    """Exponential decay weight (half-life ≈ 30 days).  Returns 1.0 for None."""
    if not timestamp:
        return 1.0
    t = _parse_timestamp(timestamp)
    if not t:
        return 1.0
    age_days = (now - t).total_seconds() / 86400.0
    return math.exp(-age_days / 30.0)


def predict_next_commands(
    db_path: Path,
    config: WarpConfig,
    last_command: Optional[str] = None,
    cwd: Optional[str] = None,
    repo_root: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = 5,
) -> list[PredictedCommand]:
    """Predict likely next commands based on history patterns.

    Two complementary signals are combined:

    1. **Sequential transitions** – what commands have historically followed
       *last_command* (or commands with the same verb) within the same
       session or a short time window.

    2. **Context frequency** – what commands are run most often in the
       current *cwd* / *repo_root*, weighted by recency and success.

    Each candidate is lightly contextualised: if the historic command
    referenced the old working directory that path is replaced with *cwd*.

    Args:
        db_path: Path to the SQLite database.
        config: Warp configuration.
        last_command: The most recently executed command.  When *None* the
            function still returns context-frequency predictions.
        cwd: Current working directory used for context scoring and command
            substitution.
        repo_root: Git repository root for repo-level context bonus.
        session_id: Shell session identifier (optional; used to retrieve
            the last command when *last_command* is not supplied).
        limit: Maximum number of predictions to return.

    Returns:
        A list of :class:`PredictedCommand` objects, sorted by descending
        score, with at most *limit* entries.
    """
    now = datetime.now(tz=timezone.utc)

    # Accumulate scores: norm_command → {score, reasons, best_command}
    candidates: dict[str, dict] = defaultdict(
        lambda: {"score": 0.0, "reasons": [], "command": ""}
    )

    def _add(cmd: str, delta: float, reason: str, old_cwd: str = "") -> None:
        """Add *delta* score to *cmd*, contextualising CWD if needed."""
        adjusted = _contextualize(cmd, old_cwd, cwd or "")
        norm = normalize_command(adjusted)
        if not norm:
            return
        entry = candidates[norm]
        entry["score"] += delta
        if reason not in entry["reasons"]:
            entry["reasons"].append(reason)
        if not entry["command"]:
            entry["command"] = adjusted

    last_norm = normalize_command(last_command) if last_command else ""
    last_verb = extract_verb(last_command) if last_command else ""

    # ------------------------------------------------------------------
    # Signal 1: sequential transitions
    # ------------------------------------------------------------------
    # Build a lookup: prev_norm → [(recency_weight, next_cmd, next_cwd)]
    #             and prev_verb → [(recency_weight, next_cmd, next_cwd)]
    transitions_by_norm: dict[str, list[tuple[float, str, str]]] = defaultdict(list)
    transitions_by_verb: dict[str, list[tuple[float, str, str]]] = defaultdict(list)

    with get_connection(db_path) as conn:
        seq_rows = get_command_sequences(conn, limit=2000)

    for row in seq_rows:
        next_cmd = row["next_cmd"]
        if not next_cmd:
            continue  # last command in dataset – no follower

        if not _is_valid_sequence(
            row["prev_session_id"],
            row["next_session_id"],
            row["prev_ts"],
            row["next_ts"],
        ):
            continue

        w = _recency_weight(row["next_ts"], now)
        prev_norm = normalize_command(row["prev_cmd"] or "")
        prev_verb = row["prev_verb"] or extract_verb(row["prev_cmd"] or "")
        next_cwd = row["next_cwd"] or ""

        transitions_by_norm[prev_norm].append((w, next_cmd, next_cwd))
        if prev_verb:
            transitions_by_verb[prev_verb].append((w, next_cmd, next_cwd))

    if last_command:
        # Exact previous-command transitions (highest weight)
        for w, next_cmd, next_cwd in transitions_by_norm.get(last_norm, []):
            label = f"follows '{last_norm[:40]}'"
            _add(next_cmd, w * 3.0, label, next_cwd)

        # Verb-level transitions (medium weight)
        if last_verb:
            for w, next_cmd, next_cwd in transitions_by_verb.get(last_verb, []):
                _add(next_cmd, w * 2.0, f"follows '{last_verb}' commands", next_cwd)

    # ------------------------------------------------------------------
    # Signal 2: context frequency (cwd / repo)
    # ------------------------------------------------------------------
    with get_connection(db_path) as conn:
        recent_rows = get_recent_commands(conn, limit=500)

    for row in recent_rows:
        sr = row_to_search_result(row)
        if not sr.success:
            continue
        w = _recency_weight(sr.timestamp, now)
        if cwd and sr.cwd == cwd:
            _add(sr.command_raw, w * 1.5, "frequent in this directory", sr.cwd)
        elif repo_root and sr.repo_root == repo_root:
            _add(sr.command_raw, w * 1.0, "frequent in this repo", sr.cwd)

    # ------------------------------------------------------------------
    # Assemble, filter, and rank
    # ------------------------------------------------------------------
    predictions: list[PredictedCommand] = [
        PredictedCommand(
            command=entry["command"],
            score=entry["score"],
            reasons=entry["reasons"],
        )
        for entry in candidates.values()
        if entry["command"]
    ]

    # Remove the last command itself from suggestions
    if last_norm:
        predictions = [
            p for p in predictions if normalize_command(p.command) != last_norm
        ]

    predictions.sort(key=lambda p: p.score, reverse=True)
    return predictions[:limit]
