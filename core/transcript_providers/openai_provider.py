import os
from pathlib import Path
from typing import Any, Dict

import aiohttp

from core.transcript_providers.base import TranscriptProvider, TranscriptResult
from utils.logger import setup_logger

logger = setup_logger("OpenAITranscriptProvider")


class OpenAITranscriptProvider(TranscriptProvider):
    """Transcription via OpenAI-compatible HTTP API (e.g. gpt-4o-mini-transcribe)."""

    def __init__(self, config: Dict[str, Any]):
        self._config = config

    @property
    def name(self) -> str:
        return "openai_api"

    def is_available(self) -> bool:
        return bool(self._resolve_api_key())

    def _resolve_api_key(self) -> str:
        env_name = str(self._config.get("api_key_env", "OPENAI_API_KEY")).strip()
        if env_name:
            env_val = os.getenv(env_name, "").strip()
            if env_val:
                return env_val
        return str(self._config.get("api_key", "")).strip()

    def _api_url(self) -> str:
        url = str(
            self._config.get("api_url", "https://api.openai.com/v1/audio/transcriptions")
        ).strip()
        return url or "https://api.openai.com/v1/audio/transcriptions"

    async def transcribe(
        self,
        media_path: Path,
        *,
        language: str = "zh",
        model: str = "",
    ) -> TranscriptResult:
        api_key = self._resolve_api_key()
        if not api_key:
            return TranscriptResult(
                text="[转录失败 - 缺少 API key]",
                provider=self.name,
                model=model,
            )

        effective_model = model or str(self._config.get("model", "gpt-4o-mini-transcribe")).strip()

        form = aiohttp.FormData()
        form.add_field("model", effective_model)
        form.add_field("response_format", "json")
        language_hint = language or str(self._config.get("language_hint", "")).strip()
        if language_hint:
            form.add_field("language", language_hint)

        content_type = _guess_content_type(media_path)
        with media_path.open("rb") as f:
            form.add_field("file", f, filename=media_path.name, content_type=content_type)
            timeout = aiohttp.ClientTimeout(total=600)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self._api_url(),
                    data=form,
                    headers={"Authorization": f"Bearer {api_key}"},
                ) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.error("OpenAI transcription failed: status=%s body=%s", resp.status, body[:300])
                        return TranscriptResult(
                            text=f"[转录失败 - HTTP {resp.status}]",
                            provider=self.name,
                            model=effective_model,
                        )
                    payload = await resp.json(content_type=None)

        text = str(payload.get("text", "")).strip()
        return TranscriptResult(
            text=text or "[转录为空]",
            language=language_hint,
            model=effective_model,
            provider=self.name,
        )


def _guess_content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".mp4": "video/mp4",
        ".m4a": "audio/mp4",
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".mov": "video/quicktime",
        ".m4v": "video/mp4",
    }.get(suffix, "application/octet-stream")
