"""Retrieval layer for warp: fetches contextually relevant commands."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from warp.config import WarpConfig
from warp.db import (
    fts_search,
    get_commands_by_repo,
    get_connection,
    get_recent_commands,
    row_to_search_result,
)
from warp.models import RetrievedCommand, SearchResult
from warp.ranking import RankingContext, score_result


def _rows_to_retrieved(rows, query: str = "") -> list[RetrievedCommand]:
    """Convert db rows to RetrievedCommand objects."""
    results = []
    for row in rows:
        sr = row_to_search_result(row)
        results.append(
            RetrievedCommand(
                command_raw=sr.command_raw,
                cwd=sr.cwd,
                timestamp=sr.timestamp,
                success=sr.success,
                relevance_score=sr.score,
                repo_root=sr.repo_root,
            )
        )
    return results


def retrieve_similar_commands(
    query: str,
    db_path: Path,
    config: WarpConfig,
    cwd: Optional[str] = None,
    repo_root: Optional[str] = None,
    limit: int = 10,
) -> list[RetrievedCommand]:
    """Retrieve commands similar to the query using FTS + ranking.

    This is the primary retrieval function used for AI grounding.
    Provides a clean extension point for embedding-based retrieval.
    """
    ctx = RankingContext(query=query, cwd=cwd, repo_root=repo_root)

    with get_connection(db_path) as conn:
        rows = fts_search(conn, query, limit=limit * 3)
        if not rows:
            recent = get_recent_commands(conn, limit=100)
            q_lower = query.lower()
            rows = [r for r in recent if q_lower in (r["command_raw"] or "").lower()]

        scored: list[tuple[float, object]] = []
        for row in rows:
            sr = row_to_search_result(row)
            fts_score = row["fts_score"] if "fts_score" in row.keys() else 0.0
            s, _ = score_result(sr, ctx, fts_score=fts_score)
            sr.score = s
            scored.append((s, row))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_rows = [row for _, row in scored[:limit]]
        results = _rows_to_retrieved(top_rows, query=query)
        for r, (s, _) in zip(results, scored[:limit]):
            r.relevance_score = s
        return results


def retrieve_recent_context(
    db_path: Path,
    limit: int = 20,
    cwd: Optional[str] = None,
) -> list[RetrievedCommand]:
    """Return the most recent commands for context injection."""
    with get_connection(db_path) as conn:
        rows = get_recent_commands(conn, limit=limit, cwd=cwd)
        return _rows_to_retrieved(rows)


def retrieve_repo_commands(
    db_path: Path,
    repo_root: str,
    limit: int = 20,
) -> list[RetrievedCommand]:
    """Return recent commands from a given git repo."""
    with get_connection(db_path) as conn:
        rows = get_commands_by_repo(conn, repo_root, limit=limit)
        return _rows_to_retrieved(rows)


def retrieve_successful_patterns(
    query: str,
    db_path: Path,
    config: WarpConfig,
    limit: int = 10,
) -> list[RetrievedCommand]:
    """Retrieve only successful commands matching the query."""
    ctx = RankingContext(query=query)
    with get_connection(db_path) as conn:
        rows = fts_search(conn, query, limit=limit * 3)
        successful = [r for r in rows if r["success"] == 1]
        if not successful:
            recent = get_recent_commands(conn, limit=200)
            q_lower = query.lower()
            successful = [
                r for r in recent
                if r["success"] == 1 and q_lower in (r["command_raw"] or "").lower()
            ]
        scored: list[tuple[float, object]] = []
        for row in successful:
            sr = row_to_search_result(row)
            fts_score = row["fts_score"] if "fts_score" in row.keys() else 0.0
            s, _ = score_result(sr, ctx, fts_score=fts_score)
            scored.append((s, row))
        scored.sort(key=lambda x: x[0], reverse=True)
        return _rows_to_retrieved([row for _, row in scored[:limit]])
