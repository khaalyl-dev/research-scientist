"""
Text utilities — chunking and light cleanup for embedding / prompts.
"""

from __future__ import annotations

import re


def clean_text(text: str) -> str:
    """Normalize whitespace for more stable embeddings and prompts."""
    if not text:
        return ""
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[str]:
    """Split text into overlapping character chunks for FAISS indexing.

    MVP uses simple character windows (not tokenizers) — fast, dependency-free,
    and good enough for all-MiniLM-L6-v2 on research abstracts / scraped pages.
    Empty or short inputs return a single cleaned chunk (or [] if empty).
    """
    cleaned = clean_text(text)
    if not cleaned:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")

    if len(cleaned) <= chunk_size:
        return [cleaned]

    chunks: list[str] = []
    start = 0
    step = chunk_size - overlap
    while start < len(cleaned):
        end = start + chunk_size
        chunks.append(cleaned[start:end].strip())
        if end >= len(cleaned):
            break
        start += step
    return [c for c in chunks if c]
