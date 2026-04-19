"""OpenAI-backed model backend for warp."""
from __future__ import annotations

import json
import os
from typing import Any, Optional

from warp.backends.model_base import ModelBackend
from warp.structured_output import parse_model_response


_SYSTEM_PROMPT = """You are Warp, a local-first AI terminal assistant.
When asked to generate shell commands, output ONLY valid JSON matching this schema:
{
  "candidates": [
    {
      "command": "<shell command>",
      "explanation": "<what it does>",
      "assumptions": "<any assumptions made>",
      "confidence": <0.0-1.0>,
      "risk_notes": "<any risk notes>"
    }
  ]
}
Generate 1-3 candidates. Do NOT execute commands. Output JSON only."""


class OpenAIBackend(ModelBackend):
    """Backend that uses the OpenAI API for command generation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model
        self._client = None

    def _get_client(self):
        """Lazily initialize the OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError as e:
                raise ImportError(
                    "openai package is required for the openai backend. "
                    "Install it with: pip install 'warp[openai]'"
                ) from e
        return self._client

    def _build_user_message(self, context: dict) -> str:
        """Build the user message from context."""
        parts = [f"Request: {context.get('request', '')}"]
        if context.get("cwd"):
            parts.append(f"Current directory: {context['cwd']}")
        if context.get("shell"):
            parts.append(f"Shell: {context['shell']}")
        if context.get("repo_root"):
            parts.append(f"Git repo: {context['repo_root']}")
        if context.get("retrieved_commands"):
            cmds = context["retrieved_commands"][:5]
            examples = "\n".join(f"  - {c}" for c in cmds)
            parts.append(f"Relevant past commands:\n{examples}")
        if context.get("preference_summary"):
            parts.append(f"User preferences: {context['preference_summary']}")
        return "\n".join(parts)

    def generate_candidates(self, context: dict) -> dict:
        """Generate candidates via the OpenAI API."""
        client = self._get_client()
        user_msg = self._build_user_message(context)
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.2,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or ""
            return parse_model_response(raw)
        except Exception as e:
            return {
                "candidates": [],
                "error": str(e),
            }

    def explain_command(self, context: dict) -> dict:
        """Explain a command via the OpenAI API."""
        client = self._get_client()
        command = context.get("command", "")
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a shell command explainer. "
                            "Explain what the given command does in plain English. "
                            "Output JSON: {\"explanation\": \"...\", \"warnings\": [...], \"risk_level\": \"low|moderate|high\"}"
                        ),
                    },
                    {"role": "user", "content": f"Explain: {command}"},
                ],
                temperature=0.1,
                max_tokens=512,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or "{}"
            return json.loads(raw)
        except Exception as e:
            from warp.explain import explain_command
            result = explain_command(command)
            return {
                "explanation": result["explanation"],
                "warnings": result["warnings"],
                "risk_level": result["risk_level"],
            }
