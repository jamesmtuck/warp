"""Abstract interface for warp model backends."""
from __future__ import annotations

from abc import ABC, abstractmethod


class ModelBackend(ABC):
    """Abstract base class for all AI/rule backends."""

    @abstractmethod
    def generate_candidates(self, context: dict) -> dict:
        """Generate command candidates from context.

        Args:
            context: Dict with at least 'request', 'shell', 'cwd' keys.

        Returns:
            Dict with 'candidates' list, each item having:
            command, explanation, assumptions, confidence, risk_notes.
        """
        ...

    @abstractmethod
    def explain_command(self, context: dict) -> dict:
        """Explain a command.

        Args:
            context: Dict with 'command' key.

        Returns:
            Dict with 'explanation', 'warnings', 'risk_level' keys.
        """
        ...

    def refine_command(self, context: dict) -> dict:
        """Refine an existing command candidate.

        Optional method; default implementation re-generates candidates.
        """
        return self.generate_candidates(context)
