"""Deterministic history search for warp."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from warp.config import WarpConfig
from warp.db import fts_search, get_connection, get_recent_commands, row_to_search_result
from warp.models import SearchResult
from warp.ranking import RankingContext, score_result


def search_history(
    query: str,
    db_path: Path,
    config: WarpConfig,
    cwd: Optional[str] = None,
    repo_root: Optional[str] = None,
    limit: Optional[int] = None,
) -> list[SearchResult]:
    """Search command history using FTS + ranking.

    Falls back to recent commands if FTS returns no results.
    """
    max_results = limit or config.max_search_results
    ctx = RankingContext(query=query, cwd=cwd, repo_root=repo_root)

    with get_connection(db_path) as conn:
        rows = fts_search(conn, query, limit=max_results * 3)

        if not rows:
            # Fallback: scan recent commands for substring match
            recent = get_recent_commands(conn, limit=200)
            q_lower = query.lower()
            rows = [r for r in recent if q_lower in (r["command_raw"] or "").lower()]

        results: list[tuple[float, SearchResult]] = []
        for row in rows:
            sr = row_to_search_result(row)
            fts_score = row["fts_score"] if "fts_score" in row.keys() else 0.0
            s, reasons = score_result(sr, ctx, fts_score=fts_score)
            sr.score = s
            sr.score_reasons = reasons
            results.append((s, sr))

        results.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in results[:max_results]]
