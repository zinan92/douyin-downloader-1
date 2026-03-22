"""Unified pipeline: input resolution -> fetch/download -> transcript -> archive -> analysis.

Supports three input types:
  1. Douyin video URL — download + transcribe + archive + analyze
  2. Douyin user profile URL — batch download all videos, then process each
  3. Local media file — skip download, go straight to transcribe + archive + analyze

The pipeline does NOT replace the existing download flow. Instead, it wraps it:
- For Douyin URLs, it delegates to the existing downloader infrastructure
- For local files, it handles everything directly
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.analysis_manager import AnalysisManager
from core.archive_manager import ArchiveManager
from core.transcript_formatter import format_transcript
from core.transcript_providers.base import TranscriptProvider, TranscriptResult
from core.transcript_providers.local_whisper_provider import LocalWhisperProvider
from core.transcript_providers.openai_provider import OpenAITranscriptProvider
from utils.logger import setup_logger

logger = setup_logger("Pipeline")

LOCAL_MEDIA_EXTENSIONS = {".mp4", ".mov", ".m4v", ".mp3", ".wav", ".m4a", ".aac"}


@dataclass
class PipelineResult:
    """Immutable-ish result of a single pipeline run."""

    source: str = ""
    source_type: str = ""  # "video", "user", "local"
    items_total: int = 0
    items_success: int = 0
    items_failed: int = 0
    outputs: List[Dict[str, Any]] = field(default_factory=list)


def is_local_media(path_str: str) -> bool:
    """Check if the input is a local media file."""
    p = Path(path_str)
    return p.exists() and p.is_file() and p.suffix.lower() in LOCAL_MEDIA_EXTENSIONS


def create_transcript_provider(config: Dict[str, Any]) -> TranscriptProvider:
    """Create the appropriate transcript provider based on config.

    Config section: transcript.provider
      - "local" or "local_whisper" → LocalWhisperProvider
      - "openai" or "openai_api"  → OpenAITranscriptProvider
      - "auto" (default)          → try local first, fall back to openai
    """
    transcript_cfg = config.get("transcript", {}) or {}
    provider_name = str(transcript_cfg.get("provider", "auto")).strip().lower()

    if provider_name in ("local", "local_whisper"):
        model = str(transcript_cfg.get("local_model", "small")).strip()
        return LocalWhisperProvider(default_model=model)

    if provider_name in ("openai", "openai_api"):
        return OpenAITranscriptProvider(transcript_cfg)

    # "auto" — prefer local, fall back to openai
    local = LocalWhisperProvider(
        default_model=str(transcript_cfg.get("local_model", "small")).strip()
    )
    if local.is_available():
        return local

    openai = OpenAITranscriptProvider(transcript_cfg)
    if openai.is_available():
        return openai

    # Return local anyway — it will produce a clear error message
    return local


async def process_local_file(
    file_path: Path,
    *,
    config: Dict[str, Any],
    provider: Optional[TranscriptProvider] = None,
    output_dir: Optional[Path] = None,
    database: Optional[Any] = None,
) -> Dict[str, Any]:
    """Process a single local media file through the pipeline.

    Returns a dict with keys: status, transcript_path, markdown_path, analysis_path, error
    """
    transcript_cfg = config.get("transcript", {}) or {}
    archive_cfg = config.get("archive", {}) or {}
    analysis_cfg = config.get("analysis", {}) or {}

    if provider is None:
        provider = create_transcript_provider(config)

    base_output = output_dir or file_path.parent
    base_output.mkdir(parents=True, exist_ok=True)

    title = file_path.stem
    language = str(transcript_cfg.get("language_hint", "zh")).strip() or "zh"

    result: Dict[str, Any] = {
        "source": str(file_path),
        "source_type": "local",
        "title": title,
        "status": "pending",
    }

    # --- Stage: Transcript ---
    transcript_result = await provider.transcribe(
        file_path, language=language
    )

    transcript_text = transcript_result.text
    result["transcript_provider"] = transcript_result.provider
    result["transcript_model"] = transcript_result.model

    # Write transcript txt
    txt_path = base_output / f"{title}.transcript.txt"
    txt_path.write_text(
        format_transcript(transcript_text), encoding="utf-8"
    )
    result["transcript_path"] = str(txt_path)

    if not transcript_result.success:
        result["status"] = "partial"
        result["error"] = transcript_text

    # --- Stage: Archive (markdown) ---
    if archive_cfg.get("enabled", True):
        archive_mgr = ArchiveManager(archive_cfg.get("output_dir"))
        archive_dir = archive_mgr.resolve_output_dir(base_output)
        md_path = await archive_mgr.write_markdown(
            title=title,
            transcript_text=transcript_text,
            output_dir=archive_dir,
            source_type="local",
            raw=archive_cfg.get("raw", False),
        )
        if md_path:
            result["markdown_path"] = str(md_path)

    # --- Stage: Analysis ---
    if analysis_cfg.get("enabled", True):
        analysis_mgr = AnalysisManager(analysis_cfg.get("output_dir"))
        analysis_dir = analysis_mgr.resolve_output_dir(base_output)
        analysis_path = await analysis_mgr.write_analysis(
            title=title,
            source_type="local",
            transcript_path=result.get("transcript_path", ""),
            markdown_path=result.get("markdown_path", ""),
            transcript_text=transcript_text,
            output_dir=analysis_dir,
        )
        if analysis_path:
            result["analysis_path"] = str(analysis_path)

    # --- Record to database ---
    if database and (result.get("markdown_path") or result.get("analysis_path")):
        aweme_id = file_path.stem  # use filename as ID for local files
        await database.upsert_archive_record({
            "aweme_id": aweme_id,
            "source_type": "local",
            "markdown_path": result.get("markdown_path"),
            "analysis_path": result.get("analysis_path"),
        })

    if result["status"] == "pending":
        result["status"] = "success"

    return result


async def run_local_pipeline(
    paths: List[Path],
    *,
    config: Dict[str, Any],
    output_dir: Optional[Path] = None,
    database: Optional[Any] = None,
) -> PipelineResult:
    """Run the pipeline on a list of local media files."""
    provider = create_transcript_provider(config)
    pipeline_result = PipelineResult(
        source="local_files",
        source_type="local",
        items_total=len(paths),
    )

    for file_path in paths:
        logger.info("Processing local file: %s", file_path.name)
        try:
            item_result = await process_local_file(
                file_path, config=config, provider=provider,
                output_dir=output_dir, database=database,
            )
            pipeline_result.outputs.append(item_result)
            if item_result.get("status") == "success":
                pipeline_result.items_success += 1
            else:
                pipeline_result.items_failed += 1
        except Exception as exc:
            logger.error("Failed to process %s: %s", file_path, exc)
            pipeline_result.items_failed += 1
            pipeline_result.outputs.append(
                {"source": str(file_path), "status": "failed", "error": str(exc)}
            )

    return pipeline_result
