"""Build rich context for AI orchestration."""
from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Optional

from warp.config import WarpConfig
from warp.git_context import get_repo_root
from warp.models import WarpContext
from warp.preferences import build_preference_summary
from warp.retrieval import retrieve_recent_context, retrieve_similar_commands
from warp.utils import get_os_platform, get_shell


_SAFETY_POLICY = (
    "Never auto-execute commands. "
    "Prefer preview/dry-run variants for destructive operations. "
    "Always warn about rm, rm -rf, dd, mkfs, and wildcard deletions. "
    "Prefer reversible operations."
)


def build_context(
    request: str,
    db_path: Path,
    config: WarpConfig,
    cwd: Optional[str] = None,
    shell: Optional[str] = None,
) -> WarpContext:
    """Build a full WarpContext for a user request."""
    cwd = cwd or os.getcwd()
    shell = shell or get_shell()
    repo_root = get_repo_root(cwd)
    os_platform = get_os_platform()

    # Retrieve recent context
    recent = retrieve_recent_context(db_path, limit=10, cwd=cwd)

    # Retrieve semantically similar commands
    retrieved = retrieve_similar_commands(
        query=request,
        db_path=db_path,
        config=config,
        cwd=cwd,
        repo_root=repo_root,
        limit=8,
    )

    # Convert RetrievedCommand to SearchResult-like for preference inference
    from warp.models import SearchResult
    recent_sr = [
        SearchResult(
            id=0,
            command_raw=r.command_raw,
            command_norm=r.command_raw,
            cwd=r.cwd,
            timestamp=r.timestamp,
            exit_code=0,
            success=r.success,
            repo_root=r.repo_root,
        )
        for r in recent
    ]
    pref_summary = build_preference_summary(recent_sr)

    return WarpContext(
        request=request,
        shell=shell,
        cwd=cwd,
        os_platform=os_platform,
        repo_root=repo_root,
        recent_commands=recent_sr,
        retrieved_commands=retrieved,
        preference_summary=pref_summary,
        safety_policy=_SAFETY_POLICY,
    )
