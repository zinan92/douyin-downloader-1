"""TranscriptManager — orchestrates transcription, archiving, and analysis for downloaded videos.

Integrates with the existing download flow (BaseDownloader._download_aweme_assets calls
transcript_manager.process_video). Now supports both OpenAI API and local whisper providers,
plus markdown archive and analysis outputs.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiofiles
import aiohttp

from config import ConfigLoader
from core.analysis_manager import AnalysisManager
from core.archive_manager import ArchiveManager
from core.transcript_formatter import format_transcript
from core.transcript_providers.base import TranscriptProvider, TranscriptResult
from core.transcript_providers.local_whisper_provider import LocalWhisperProvider
from core.transcript_providers.openai_provider import OpenAITranscriptProvider
from storage import Database, FileManager
from utils.logger import setup_logger

logger = setup_logger("TranscriptManager")


class TranscriptManager:
    def __init__(
        self,
        config: ConfigLoader,
        file_manager: FileManager,
        database: Optional[Database] = None,
    ):
        self.config = config
        self.file_manager = file_manager
        self.database = database
        self._provider: Optional[TranscriptProvider] = None

    def _cfg(self) -> Dict[str, Any]:
        return self.config.get("transcript", {}) or {}

    def _archive_cfg(self) -> Dict[str, Any]:
        return self.config.get("archive", {}) or {}

    def _analysis_cfg(self) -> Dict[str, Any]:
        return self.config.get("analysis", {}) or {}

    def _enabled(self) -> bool:
        return bool(self._cfg().get("enabled", False))

    def _model(self) -> str:
        return str(self._cfg().get("model", "gpt-4o-mini-transcribe")).strip()

    def _response_formats(self) -> List[str]:
        formats = self._cfg().get("response_formats", ["txt", "json"])
        if not isinstance(formats, list):
            return ["txt", "json"]
        normalized = [str(item).strip().lower() for item in formats if str(item).strip()]
        return normalized or ["txt", "json"]

    def _get_provider(self) -> TranscriptProvider:
        """Lazily create the transcript provider based on config."""
        if self._provider is not None:
            return self._provider

        cfg = self._cfg()
        provider_name = str(cfg.get("provider", "openai_api")).strip().lower()

        if provider_name in ("local", "local_whisper"):
            local_model = str(cfg.get("local_model", "small")).strip()
            self._provider = LocalWhisperProvider(default_model=local_model)
        elif provider_name == "auto":
            local_model = str(cfg.get("local_model", "small")).strip()
            local = LocalWhisperProvider(default_model=local_model)
            if local.is_available():
                self._provider = local
            else:
                self._provider = OpenAITranscriptProvider(cfg)
        else:
            # Default: openai_api (backward compatible)
            self._provider = OpenAITranscriptProvider(cfg)

        return self._provider

    def resolve_output_dir(self, video_path: Path) -> Path:
        video_path = Path(video_path)
        video_dir = video_path.parent
        output_dir = str(self._cfg().get("output_dir", "")).strip()
        if not output_dir:
            return video_dir

        output_root = Path(output_dir)
        try:
            relative_dir = video_dir.resolve().relative_to(
                self.file_manager.base_path.resolve()
            )
            return output_root / relative_dir
        except Exception:
            logger.warning(
                "Failed to mirror transcript path for video %s, fallback to video dir",
                video_path,
            )
            return video_dir

    def build_output_paths(self, video_path: Path) -> Tuple[Path, Path]:
        video_path = Path(video_path)
        output_dir = self.resolve_output_dir(video_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = video_path.stem
        return (
            output_dir / f"{stem}.transcript.txt",
            output_dir / f"{stem}.transcript.json",
        )

    async def process_video(
        self,
        video_path: Path,
        aweme_id: str,
        *,
        title: str = "",
        author: str = "",
        publish_date: str = "",
        source_url: str = "",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        video_path = Path(video_path)

        if not self._enabled():
            return {"status": "skipped", "reason": "disabled"}

        text_path, json_path = self.build_output_paths(video_path)
        provider = self._get_provider()
        model_name = self._model()
        language = str(self._cfg().get("language_hint", "")).strip() or "zh"

        # --- Transcription ---
        try:
            transcript_result = await provider.transcribe(
                video_path, language=language, model=model_name
            )
            text = transcript_result.text
            formatted_text = format_transcript(text)

            await self._write_outputs(
                {"text": text}, text_path, json_path, formatted_text=formatted_text
            )

            status = "success" if transcript_result.success else "failed"

            await self._record_job(
                aweme_id=aweme_id,
                video_path=video_path,
                transcript_dir=text_path.parent,
                text_path=text_path,
                json_path=json_path,
                model=transcript_result.model or model_name,
                status=status,
                skip_reason=None,
                error_message=None if transcript_result.success else text,
            )

            result: Dict[str, Any] = {
                "status": status,
                "text_path": str(text_path),
                "json_path": str(json_path),
                "provider": transcript_result.provider,
            }

            # --- Archive (markdown) ---
            archive_cfg = self._archive_cfg()
            if archive_cfg.get("enabled", True) and transcript_result.success:
                archive_mgr = ArchiveManager(archive_cfg.get("output_dir"))
                archive_dir = archive_mgr.resolve_output_dir(text_path.parent)
                md_path = await archive_mgr.write_markdown(
                    title=title or video_path.stem,
                    transcript_text=text,
                    output_dir=archive_dir,
                    aweme_id=aweme_id,
                    source_url=source_url,
                    author=author,
                    publish_date=publish_date,
                    tags=tags,
                    raw=archive_cfg.get("raw", False),
                )
                if md_path:
                    result["markdown_path"] = str(md_path)

            # --- Analysis ---
            analysis_cfg = self._analysis_cfg()
            if analysis_cfg.get("enabled", True) and transcript_result.success:
                analysis_mgr = AnalysisManager(analysis_cfg.get("output_dir"))
                analysis_dir = analysis_mgr.resolve_output_dir(text_path.parent)
                analysis_path = await analysis_mgr.write_analysis(
                    title=title or video_path.stem,
                    author=author,
                    aweme_id=aweme_id,
                    publish_time=publish_date,
                    source_url=source_url,
                    transcript_path=str(text_path),
                    markdown_path=result.get("markdown_path", ""),
                    tags=tags,
                    transcript_text=text,
                    output_dir=analysis_dir,
                )
                if analysis_path:
                    result["analysis_path"] = str(analysis_path)

            # --- Record archive to database ---
            if self.database and (result.get("markdown_path") or result.get("analysis_path")):
                await self.database.upsert_archive_record({
                    "aweme_id": aweme_id,
                    "source_type": "douyin",
                    "markdown_path": result.get("markdown_path"),
                    "analysis_path": result.get("analysis_path"),
                })

            return result

        except Exception as exc:
            error_message = str(exc)
            await self._record_job(
                aweme_id=aweme_id,
                video_path=video_path,
                transcript_dir=text_path.parent,
                text_path=text_path,
                json_path=json_path,
                model=model_name,
                status="failed",
                skip_reason=None,
                error_message=error_message,
            )
            logger.error("Transcript failed for aweme %s: %s", aweme_id, error_message)
            return {
                "status": "failed",
                "reason": "transcription_error",
                "error": error_message,
            }

    async def _write_outputs(
        self,
        payload: Dict[str, Any],
        text_path: Path,
        json_path: Path,
        *,
        formatted_text: str = "",
    ) -> None:
        formats = set(self._response_formats())

        if "txt" in formats:
            text = formatted_text or str(payload.get("text", "")).strip()
            async with aiofiles.open(text_path, "w", encoding="utf-8") as f:
                await f.write(text)

        if "json" in formats:
            async with aiofiles.open(json_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(payload, ensure_ascii=False, indent=2))

    async def _record_job(
        self,
        *,
        aweme_id: str,
        video_path: Path,
        transcript_dir: Path,
        text_path: Path,
        json_path: Path,
        model: str,
        status: str,
        skip_reason: Optional[str],
        error_message: Optional[str],
    ) -> None:
        if not self.database:
            return

        await self.database.upsert_transcript_job(
            {
                "aweme_id": aweme_id,
                "video_path": str(video_path),
                "transcript_dir": str(transcript_dir),
                "text_path": str(text_path),
                "json_path": str(json_path),
                "model": model,
                "status": status,
                "skip_reason": skip_reason,
                "error_message": error_message,
            }
        )
