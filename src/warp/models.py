"""Core data models for warp."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CaptureRecord:
    """Represents a single captured shell command with its metadata."""

    timestamp: str
    session_id: str
    shell: str
    cwd: str
    hostname: str
    username: str
    command_raw: str
    command_norm: str
    exit_code: int
    success: int
    repo_root: Optional[str] = None
    verb: Optional[str] = None
    duration_ms: Optional[int] = None


@dataclass
class SearchResult:
    """Represents a search result from the command history."""

    id: int
    command_raw: str
    command_norm: str
    cwd: str
    timestamp: str
    exit_code: int
    success: int
    score: float = 0.0
    score_reasons: list[str] = field(default_factory=list)
    repo_root: Optional[str] = None
    verb: Optional[str] = None
    session_id: str = ""
    shell: str = ""
    hostname: str = ""
    username: str = ""
    duration_ms: Optional[int] = None


@dataclass
class CandidateCommand:
    """Represents an AI-generated or rule-generated command candidate."""

    command: str
    explanation: str
    assumptions: str
    confidence: float
    risk_level: str
    risk_warnings: list[str] = field(default_factory=list)
    safer_preview: Optional[str] = None
    risk_notes: str = ""


@dataclass
class WarpContext:
    """Full context object used for AI orchestration."""

    request: str
    shell: str
    cwd: str
    os_platform: str
    repo_root: Optional[str] = None
    recent_commands: list[SearchResult] = field(default_factory=list)
    retrieved_commands: list[SearchResult] = field(default_factory=list)
    preference_summary: str = ""
    safety_policy: str = ""


@dataclass
class RetrievedCommand:
    """A retrieved command with relevance score for use in prompting."""

    command_raw: str
    cwd: str
    timestamp: str
    success: int
    relevance_score: float = 0.0
    repo_root: Optional[str] = None
