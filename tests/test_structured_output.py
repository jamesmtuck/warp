"""Tests for structured_output module."""
import json
import pytest
from warp.structured_output import candidates_from_parsed, parse_model_response


def test_parse_valid_response():
    raw = json.dumps({
        "candidates": [
            {
                "command": "ls -la",
                "explanation": "List files",
                "assumptions": "",
                "confidence": 0.9,
                "risk_notes": "",
            }
        ]
    })
    result = parse_model_response(raw)
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["command"] == "ls -la"


def test_parse_empty_response_raises():
    with pytest.raises(ValueError):
        parse_model_response("")


def test_parse_non_json_raises():
    with pytest.raises(ValueError):
        parse_model_response("this is not json at all !!!!")


def test_parse_response_repairs_json():
    # JSON embedded in text
    raw = 'Here is the result: {"candidates": [{"command": "ls", "explanation": "list"}]}'
    result = parse_model_response(raw)
    assert len(result["candidates"]) == 1


def test_parse_filters_incomplete_candidates():
    raw = json.dumps({
        "candidates": [
            {"command": "ls", "explanation": "list"},
            {"command": "ps"},  # missing explanation -> filtered
            {"explanation": "foo"},  # missing command -> filtered
        ]
    })
    result = parse_model_response(raw)
    assert len(result["candidates"]) == 1


def test_candidates_from_parsed_runs_safety():
    parsed = {
        "candidates": [
            {
                "command": "rm -rf /tmp",
                "explanation": "delete tmp",
                "assumptions": "",
                "confidence": 0.8,
                "risk_notes": "",
            }
        ]
    }
    candidates = candidates_from_parsed(parsed)
    assert len(candidates) == 1
    assert candidates[0].risk_level == "high"
    assert len(candidates[0].risk_warnings) > 0
