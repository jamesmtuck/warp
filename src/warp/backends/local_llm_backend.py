"""Placeholder local LLM backend for warp."""
from __future__ import annotations

import json
from typing import Optional

from warp.backends.model_base import ModelBackend


class LocalLLMBackend(ModelBackend):
    """Adapter for a locally-running LLM (e.g. llama.cpp, Ollama).

    This is a placeholder implementation. To enable real local inference,
    configure `local_llm_url` in config and implement the HTTP call below.
    """

    def __init__(self, base_url: Optional[str] = None, model: str = "llama3") -> None:
        self.base_url = base_url or "http://localhost:11434"
        self.model = model

    def generate_candidates(self, context: dict) -> dict:
        """Generate candidates from a local LLM endpoint."""
        try:
            import urllib.request
            import urllib.error

            prompt = (
                f"Generate 1-3 shell commands for: {context.get('request', '')}\n"
                f"CWD: {context.get('cwd', '.')}\n"
                "Output JSON: {\"candidates\": [{\"command\": ..., \"explanation\": ..., "
                "\"assumptions\": ..., \"confidence\": 0.8, \"risk_notes\": \"\"}]}"
            )
            payload = json.dumps(
                {"model": self.model, "prompt": prompt, "stream": False}
            ).encode()
            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode())
                raw = body.get("response", "{}")
                from warp.structured_output import parse_model_response
                return parse_model_response(raw)
        except Exception as e:
            return {"candidates": [], "error": str(e)}

    def explain_command(self, context: dict) -> dict:
        """Fall back to rule-based explanation."""
        from warp.explain import explain_command
        command = context.get("command", "")
        result = explain_command(command)
        return {
            "explanation": result["explanation"],
            "warnings": result["warnings"],
            "risk_level": result["risk_level"],
        }
