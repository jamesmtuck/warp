"""Ranking logic for command search results."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from warp.models import SearchResult


@dataclass
class RankingContext:
    """Context used to score search results."""

    query: str
    cwd: Optional[str] = None
    repo_root: Optional[str] = None
    now: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.now is None:
            self.now = datetime.now(tz=timezone.utc)


def _parse_timestamp(ts: str) -> Optional[datetime]:
    """Parse an ISO 8601 timestamp string."""
    try:
        ts = ts.rstrip("Z")
        return datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        return None


def score_result(
    result: SearchResult,
    ctx: RankingContext,
    fts_score: float = 0.0,
) -> tuple[float, list[str]]:
    """Score a search result given a ranking context.

    Returns (score, list_of_score_reason_strings).
    Higher is better.
    """
    reasons: list[str] = []
    score = 0.0

    # FTS / keyword similarity (bm25 is negative in SQLite, flip sign)
    if fts_score != 0.0:
        fts_contrib = max(0.0, -fts_score)
        score += fts_contrib
        reasons.append(f"fts={fts_contrib:.2f}")

    query_lower = ctx.query.lower()
    raw_lower = result.command_raw.lower()

    # Exact substring bonus
    if query_lower in raw_lower:
        score += 5.0
        reasons.append("exact_substring")

    # Verb match bonus
    if result.verb and query_lower.startswith(result.verb.lower()):
        score += 2.0
        reasons.append("verb_match")

    # cwd bonus
    if ctx.cwd and result.cwd == ctx.cwd:
        score += 3.0
        reasons.append("same_cwd")

    # repo_root bonus
    if ctx.repo_root and result.repo_root == ctx.repo_root:
        score += 2.0
        reasons.append("same_repo")

    # Success bonus
    if result.success:
        score += 1.0
        reasons.append("success")

    # Recency decay (exponential half-life of ~30 days)
    if result.timestamp and ctx.now:
        ts = _parse_timestamp(result.timestamp)
        if ts:
            age_days = (ctx.now - ts).total_seconds() / 86400.0
            recency = math.exp(-age_days / 30.0)
            score += recency * 2.0
            reasons.append(f"recency={recency:.2f}")

    return score, reasons
