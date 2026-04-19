"""Placeholder embeddings abstraction for future semantic retrieval."""
from __future__ import annotations

from typing import Optional


def embed_text(text: str) -> list[float]:
    """Embed a text string into a vector.

    Currently a stub. Replace with a real embedding backend
    (e.g. sentence-transformers or OpenAI embeddings) when needed.
    """
    # Stub: return an empty vector
    return []


def semantic_search(
    query: str,
    db_path: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """Semantic search using embeddings.

    Currently a stub that returns an empty list.
    Implement by storing embeddings in SQLite and computing cosine similarity.
    """
    return []
