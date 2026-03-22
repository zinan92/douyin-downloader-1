"""Analysis stage — produces a structured JSON summary for each processed item.

First version: simple rule-based summary (no AI). Extracts metadata + first
few sentences from transcript as short_summary.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles

from utils.logger import setup_logger

logger = setup_logger("AnalysisManager")


def _extract_short_summary(transcript_text: str, max_sentences: int = 3) -> str:
    """Extract a short summary from the transcript (first N sentences)."""
    if not transcript_text or transcript_text.startswith("["):
        return ""

    import re

    sentences = re.split(r"(?<=[。！？!?\.…])\s*", transcript_text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        # Fallback: first 200 chars
        return transcript_text.strip()[:200]

    selected = sentences[:max_sentences]
    summary = "".join(selected)
    # Cap length for very long sentences
    if len(summary) > 200:
        return summary[:200]
    return summary


class AnalysisManager:
    """Generates structured JSON analysis summaries."""

    def __init__(self, output_dir: Optional[str] = None):
        self._output_dir = Path(output_dir) if output_dir else None

    def resolve_output_dir(self, fallback_dir: Path) -> Path:
        if self._output_dir:
            return self._output_dir
        return fallback_dir

    async def write_analysis(
        self,
        *,
        title: str,
        author: str = "",
        source_type: str = "douyin",
        aweme_id: str = "",
        publish_time: str = "",
        source_url: str = "",
        transcript_path: str = "",
        markdown_path: str = "",
        tags: Optional[List[str]] = None,
        transcript_text: str = "",
        output_dir: Path,
    ) -> Optional[Path]:
        """Write a structured analysis JSON file.

        Returns the path to the written file, or None on failure.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        short_summary = _extract_short_summary(transcript_text)

        analysis = {
            "title": title,
            "author": author,
            "source_type": source_type,
            "aweme_id": aweme_id,
            "publish_time": publish_time,
            "source_url": source_url,
            "transcript_path": transcript_path,
            "markdown_path": markdown_path,
            "tags": tags or [],
            "short_summary": short_summary,
            "analyzed_at": datetime.now().isoformat(timespec="seconds"),
        }

        safe_id = aweme_id or Path(transcript_path).stem if transcript_path else "unknown"
        filename = f"{safe_id}_analysis.json"
        filepath = output_dir / filename

        try:
            async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
                await f.write(json.dumps(analysis, ensure_ascii=False, indent=2))
            logger.info("Analysis written: %s", filepath.name)
            return filepath
        except Exception as exc:
            logger.error("Failed to write analysis %s: %s", filepath, exc)
            return None
