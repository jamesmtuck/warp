"""Build prompts for model backends."""
from __future__ import annotations

from warp.models import WarpContext

SYSTEM_PROMPT = """You are Warp, an AI-powered terminal assistant.
Your job is to help users find and draft shell commands.

Rules:
- Generate commands as DRAFTS ONLY. Never imply auto-execution.
- Use retrieved past commands as grounding examples.
- Prefer the user's habitual tools (e.g. rg over grep if they use rg).
- Prefer safe preview variants when the intent is ambiguous or destructive.
- Generate 1-3 candidates in order of confidence.
- Explain each command clearly and briefly.
- State any assumptions you make.
- Output ONLY valid JSON in the schema below.

Output schema:
{
  "candidates": [
    {
      "command": "<shell command string>",
      "explanation": "<plain English explanation>",
      "assumptions": "<assumptions made>",
      "confidence": <float 0.0-1.0>,
      "risk_notes": "<risk notes or empty string>"
    }
  ]
}"""


def build_user_prompt(ctx: WarpContext) -> str:
    """Build a user-facing prompt from WarpContext."""
    parts = [f"Request: {ctx.request}"]

    parts.append(f"Shell: {ctx.shell}")
    parts.append(f"OS: {ctx.os_platform}")
    parts.append(f"Current directory: {ctx.cwd}")

    if ctx.repo_root:
        parts.append(f"Git repo root: {ctx.repo_root}")

    if ctx.retrieved_commands:
        parts.append("\nRelevant past commands from history:")
        for cmd in ctx.retrieved_commands[:6]:
            status = "✓" if cmd.success else "✗"
            parts.append(f"  {status} {cmd.command_raw}  (in {cmd.cwd})")

    if ctx.preference_summary and ctx.preference_summary != "No strong preferences inferred.":
        parts.append(f"\nUser preferences: {ctx.preference_summary}")

    if ctx.safety_policy:
        parts.append(f"\nSafety policy: {ctx.safety_policy}")

    return "\n".join(parts)


def build_explain_prompt(command: str, ctx: WarpContext) -> str:
    """Build an explain prompt for a single command."""
    return (
        f"Explain this shell command in plain English, including any flags and risks:\n"
        f"  {command}\n"
        f"Shell: {ctx.shell}\nOS: {ctx.os_platform}"
    )
