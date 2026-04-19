"""Orchestration layer: ties together context, retrieval, backend, and safety."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from warp.backends.model_base import ModelBackend
from warp.backends.rule_backend import RuleBackend
from warp.config import WarpConfig
from warp.context_builder import build_context
from warp.models import CandidateCommand, WarpContext
from warp.safety import analyze_command_risk
from warp.structured_output import candidates_from_parsed


def _get_backend(config: WarpConfig) -> ModelBackend:
    """Instantiate the configured model backend."""
    backend_name = config.model_backend.lower()
    if backend_name == "openai":
        from warp.backends.openai_backend import OpenAIBackend
        return OpenAIBackend(
            api_key=config.openai_api_key,
            model=config.openai_model,
        )
    if backend_name == "local":
        from warp.backends.local_llm_backend import LocalLLMBackend
        return LocalLLMBackend(base_url=config.local_llm_url)
    return RuleBackend()


def _apply_safety(candidates: list[CandidateCommand]) -> list[CandidateCommand]:
    """Apply deterministic safety analysis to all candidates."""
    updated = []
    for c in candidates:
        risk_level, warnings, safer = analyze_command_risk(c.command)
        updated.append(
            CandidateCommand(
                command=c.command,
                explanation=c.explanation,
                assumptions=c.assumptions,
                confidence=c.confidence,
                risk_level=risk_level,
                risk_warnings=warnings,
                safer_preview=safer,
                risk_notes=c.risk_notes,
            )
        )
    return updated


def generate_candidates(
    request: str,
    db_path: Path,
    config: WarpConfig,
    cwd: Optional[str] = None,
    shell: Optional[str] = None,
) -> list[CandidateCommand]:
    """Generate command candidates for a natural language request.

    1. Build context (cwd, shell, history, retrieved commands)
    2. Call selected backend
    3. Parse structured output
    4. Apply deterministic safety analysis
    5. Return final CandidateCommand list
    """
    ctx = build_context(request, db_path, config, cwd=cwd, shell=shell)
    backend = _get_backend(config)

    context_dict = {
        "request": ctx.request,
        "shell": ctx.shell,
        "cwd": ctx.cwd,
        "os_platform": ctx.os_platform,
        "repo_root": ctx.repo_root,
        "retrieved_commands": [r.command_raw for r in ctx.retrieved_commands],
        "recent_commands": [r.command_raw for r in ctx.recent_commands],
        "preference_summary": ctx.preference_summary,
        "safety_policy": ctx.safety_policy,
    }

    raw_result = backend.generate_candidates(context_dict)
    candidates = candidates_from_parsed(raw_result)
    return _apply_safety(candidates)


def explain_candidate(
    command: str,
    db_path: Path,
    config: WarpConfig,
    cwd: Optional[str] = None,
    shell: Optional[str] = None,
) -> dict:
    """Explain a command using the configured backend + rule-based analysis."""
    ctx = build_context("explain", db_path, config, cwd=cwd, shell=shell)
    backend = _get_backend(config)
    result = backend.explain_command({"command": command, "shell": ctx.shell})
    # Always augment with deterministic safety
    risk_level, warnings, safer = analyze_command_risk(command)
    result.setdefault("warnings", [])
    result["risk_level"] = risk_level
    for w in warnings:
        if w not in result["warnings"]:
            result["warnings"].append(w)
    if safer and not result.get("safer_preview"):
        result["safer_preview"] = safer
    return result
