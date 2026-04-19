"""Validation and parsing of structured model output."""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from warp.models import CandidateCommand


_REQUIRED_CANDIDATE_FIELDS = {"command", "explanation"}


def _repair_json(raw: str) -> str:
    """Try to extract JSON from a potentially messy response."""
    # Look for a JSON block
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        return match.group(0)
    return raw


def parse_model_response(raw_response: str) -> dict[str, Any]:
    """Parse and validate a raw model JSON response.

    Returns a dict with 'candidates' key (list of candidate dicts).
    Raises ValueError on unrecoverable parse failure.
    """
    if not raw_response or not raw_response.strip():
        raise ValueError("Empty model response")

    text = raw_response.strip()

    # Try direct parse
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try repair
        repaired = _repair_json(text)
        try:
            data = json.loads(repaired)
        except json.JSONDecodeError as e:
            raise ValueError(f"Cannot parse model response as JSON: {e}") from e

    # Validate structure
    if not isinstance(data, dict):
        raise ValueError("Model response must be a JSON object")

    candidates = data.get("candidates", [])
    if not isinstance(candidates, list):
        raise ValueError("'candidates' must be a list")

    validated: list[dict[str, Any]] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        if not all(k in item for k in _REQUIRED_CANDIDATE_FIELDS):
            continue
        validated.append(item)

    data["candidates"] = validated
    return data


def candidates_from_parsed(parsed: dict[str, Any]) -> list[CandidateCommand]:
    """Convert a parsed model response dict to CandidateCommand objects."""
    from warp.safety import analyze_command_risk

    results: list[CandidateCommand] = []
    for item in parsed.get("candidates", []):
        command = item.get("command", "")
        explanation = item.get("explanation", "")
        assumptions = item.get("assumptions", "")
        confidence = float(item.get("confidence", 0.7))
        risk_notes = item.get("risk_notes", "")

        risk_level, warnings, safer_preview = analyze_command_risk(command)

        results.append(
            CandidateCommand(
                command=command,
                explanation=explanation,
                assumptions=assumptions,
                confidence=confidence,
                risk_level=risk_level,
                risk_warnings=warnings,
                safer_preview=safer_preview,
                risk_notes=risk_notes,
            )
        )
    return results
