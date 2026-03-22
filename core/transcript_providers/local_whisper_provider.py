import shutil
import subprocess
from pathlib import Path
from typing import Optional

from core.transcript_providers.base import TranscriptProvider, TranscriptResult
from utils.logger import setup_logger

logger = setup_logger("LocalWhisperProvider")

_MLX_MODEL_MAP = {
    "tiny": "mlx-community/whisper-tiny-mlx",
    "base": "mlx-community/whisper-base-mlx-q4",
    "small": "mlx-community/whisper-small-mlx",
    "medium": "mlx-community/whisper-medium-mlx",
    "large": "mlx-community/whisper-large-v3-mlx",
    "large-v3": "mlx-community/whisper-large-v3-mlx",
    "large-v3-turbo": "mlx-community/whisper-large-v3-turbo",
}


class LocalWhisperProvider(TranscriptProvider):
    """Local transcription: mlx-whisper (Apple Silicon) with openai-whisper CLI fallback."""

    def __init__(self, default_model: str = "small"):
        self._default_model = default_model
        self._mlx_available: Optional[bool] = None
        self._cli_available: Optional[bool] = None

    @property
    def name(self) -> str:
        return "local_whisper"

    def is_available(self) -> bool:
        return self._check_mlx() or self._check_cli()

    def _check_mlx(self) -> bool:
        if self._mlx_available is None:
            try:
                import mlx_whisper  # noqa: F401
                self._mlx_available = True
            except ImportError:
                self._mlx_available = False
        return self._mlx_available

    def _check_cli(self) -> bool:
        if self._cli_available is None:
            self._cli_available = shutil.which("whisper") is not None
        return self._cli_available

    async def transcribe(
        self,
        media_path: Path,
        *,
        language: str = "zh",
        model: str = "",
    ) -> TranscriptResult:
        effective_model = model or self._default_model

        # Try mlx-whisper first
        if self._check_mlx():
            result = self._transcribe_mlx(media_path, effective_model, language)
            if result.success:
                return result
            logger.warning("mlx-whisper failed, falling back to CLI whisper")

        # Fallback to openai-whisper CLI
        if self._check_cli():
            return self._transcribe_cli(media_path, effective_model, language)

        return TranscriptResult(
            text="[转录失败 - 未安装 mlx-whisper 或 whisper CLI]",
            provider=self.name,
            model=effective_model,
        )

    def _transcribe_mlx(
        self, media_path: Path, model: str, language: str
    ) -> TranscriptResult:
        try:
            import mlx_whisper

            model_id = _MLX_MODEL_MAP.get(model, _MLX_MODEL_MAP["small"])
            result = mlx_whisper.transcribe(
                str(media_path), path_or_hf_repo=model_id, language=language
            )
            text = result.get("text", "").strip()
            segments = result.get("segments", [])
            return TranscriptResult(
                text=text or "[转录为空]",
                language=language,
                model=model_id,
                provider="mlx_whisper",
                segments=segments,
            )
        except Exception as exc:
            logger.warning("mlx-whisper transcription error: %s", exc)
            return TranscriptResult(
                text=f"[mlx-whisper 失败: {exc}]",
                provider="mlx_whisper",
                model=model,
            )

    def _transcribe_cli(
        self, media_path: Path, model: str, language: str
    ) -> TranscriptResult:
        try:
            result = subprocess.run(
                [
                    "whisper",
                    str(media_path),
                    "--model", model,
                    "--language", language,
                    "--output_format", "txt",
                    "--output_dir", str(media_path.parent),
                ],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if result.returncode != 0:
                logger.warning("Whisper CLI failed: %s", result.stderr[:300])
                return TranscriptResult(
                    text="[转录失败]",
                    provider="whisper_cli",
                    model=model,
                )

            txt_file = media_path.with_suffix(".txt")
            if txt_file.exists():
                text = txt_file.read_text(encoding="utf-8").strip()
                txt_file.unlink()
                return TranscriptResult(
                    text=text or "[转录为空]",
                    language=language,
                    model=model,
                    provider="whisper_cli",
                )
            return TranscriptResult(
                text="[转录失败 - 无输出文件]",
                provider="whisper_cli",
                model=model,
            )
        except Exception as exc:
            logger.warning("Whisper CLI error: %s", exc)
            return TranscriptResult(
                text=f"[转录失败: {exc}]",
                provider="whisper_cli",
                model=model,
            )
