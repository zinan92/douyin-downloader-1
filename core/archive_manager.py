"""Markdown archive output for transcribed videos.

Generates a readable .md file per video containing metadata + formatted transcript.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles

from core.transcript_formatter import format_transcript
from utils.logger import setup_logger

logger = setup_logger("ArchiveManager")


def _safe_filename(title: str, max_len: int = 80) -> str:
    safe = re.sub(r'[\\/:*?"<>|\n\r#]', "", title)
    safe = re.sub(r"\s+", " ", safe).strip()
    return safe[:max_len].strip() if safe else "untitled"


class ArchiveManager:
    """Generates markdown archive files from video metadata + transcript."""

    def __init__(self, output_dir: Optional[str] = None):
        self._output_dir = Path(output_dir) if output_dir else None

    def resolve_output_dir(self, fallback_dir: Path) -> Path:
        if self._output_dir:
            return self._output_dir
        return fallback_dir

    async def write_markdown(
        self,
        *,
        title: str,
        transcript_text: str,
        output_dir: Path,
        aweme_id: str = "",
        source_url: str = "",
        author: str = "",
        publish_date: str = "",
        tags: Optional[List[str]] = None,
        source_type: str = "douyin",
        raw: bool = False,
    ) -> Optional[Path]:
        """Write a markdown archive file.

        Returns the path to the written file, or None on failure.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        safe_title = _safe_filename(title)
        date_prefix = f"{publish_date}_" if publish_date else ""
        id_suffix = f"_{aweme_id}" if aweme_id else ""
        filename = f"{date_prefix}{safe_title}{id_suffix}.md"
        filepath = output_dir / filename

        body = transcript_text if raw else format_transcript(transcript_text)

        lines = [f"# {title}", ""]

        # Metadata block
        meta_parts = []
        if publish_date:
            meta_parts.append(f"日期: {publish_date}")
        if author:
            meta_parts.append(f"作者: {author}")
        if source_url:
            meta_parts.append(f"来源: {source_url}")
        elif source_type == "local":
            meta_parts.append("来源: 本地文件")
        if aweme_id:
            meta_parts.append(f"ID: {aweme_id}")
        if meta_parts:
            lines.append(f"> {' | '.join(meta_parts)}")
            lines.append("")

        if tags:
            lines.append(f"**标签:** {', '.join(f'#{t}' for t in tags)}")
            lines.append("")

        lines.append(body)
        lines.append("")  # trailing newline

        content = "\n".join(lines)

        try:
            async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
                await f.write(content)
            logger.info("Markdown archive written: %s", filepath.name)
            return filepath
        except Exception as exc:
            logger.error("Failed to write markdown archive %s: %s", filepath, exc)
            return None
