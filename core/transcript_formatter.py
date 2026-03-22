"""Format raw Whisper transcript output into human-readable paragraphs.

Ported from douyin-downloader's format_transcript logic with improvements.
"""

import re
from typing import List


def format_transcript(raw_text: str) -> str:
    """Turn raw Whisper output into human-readable paragraphs.

    1. Normalises whitespace
    2. Splits on Chinese/English sentence endings
    3. Groups sentences into paragraphs (~5 sentences each)
    4. Preserves existing paragraph breaks if present
    """
    if not raw_text or raw_text.startswith("["):
        return raw_text

    text = raw_text.strip()

    # If text already has paragraph breaks, just clean up
    if "\n\n" in text:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        return "\n\n".join(paragraphs)

    # Normalise whitespace
    text = re.sub(r"\s+", " ", text)

    # Split on sentence-ending punctuation (Chinese and English)
    sentences = re.split(r"(?<=[。！？!?\.…])\s*", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if len(sentences) <= 1:
        # No sentence boundaries — try splitting on commas for long text
        if len(text) > 200:
            segments = re.split(r"(?<=[，,；;])\s*", text)
            segments = [s.strip() for s in segments if s.strip()]
            return _group_into_paragraphs(segments, group_size=6)
        return text

    return _group_into_paragraphs(sentences, group_size=5)


def _group_into_paragraphs(segments: List[str], group_size: int = 5) -> str:
    """Group a list of text segments into paragraphs."""
    paragraphs = []
    for i in range(0, len(segments), group_size):
        chunk = segments[i : i + group_size]
        paragraphs.append("".join(chunk))
    return "\n\n".join(paragraphs)
