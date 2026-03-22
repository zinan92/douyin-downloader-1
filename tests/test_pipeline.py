"""Tests for the unified pipeline."""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from core.pipeline import (
    is_local_media,
    create_transcript_provider,
    process_local_file,
    run_local_pipeline,
    PipelineResult,
    LOCAL_MEDIA_EXTENSIONS,
)
from core.transcript_providers.base import TranscriptResult
from core.transcript_providers.local_whisper_provider import LocalWhisperProvider
from core.transcript_providers.openai_provider import OpenAITranscriptProvider


class TestIsLocalMedia:
    def test_mp4_file(self, tmp_path):
        f = tmp_path / "test.mp4"
        f.write_bytes(b"fake")
        assert is_local_media(str(f)) is True

    def test_mov_file(self, tmp_path):
        f = tmp_path / "test.mov"
        f.write_bytes(b"fake")
        assert is_local_media(str(f)) is True

    def test_wav_file(self, tmp_path):
        f = tmp_path / "test.wav"
        f.write_bytes(b"fake")
        assert is_local_media(str(f)) is True

    def test_non_media_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("not media")
        assert is_local_media(str(f)) is False

    def test_nonexistent_file(self):
        assert is_local_media("/nonexistent/file.mp4") is False

    def test_url_string(self):
        assert is_local_media("https://www.douyin.com/video/123") is False


class TestCreateTranscriptProvider:
    def test_local_provider(self):
        config = {"transcript": {"provider": "local", "local_model": "tiny"}}
        p = create_transcript_provider(config)
        assert isinstance(p, LocalWhisperProvider)

    def test_openai_provider(self):
        config = {"transcript": {"provider": "openai_api", "api_key": "sk-test"}}
        p = create_transcript_provider(config)
        assert isinstance(p, OpenAITranscriptProvider)

    def test_auto_no_deps_returns_local(self):
        config = {"transcript": {"provider": "auto"}}
        p = create_transcript_provider(config)
        # auto with no deps returns local (which will give clear error on use)
        assert isinstance(p, (LocalWhisperProvider, OpenAITranscriptProvider))


class TestProcessLocalFile:
    @pytest.mark.asyncio
    async def test_process_with_mock_provider(self, tmp_path):
        # Create a fake media file
        media_file = tmp_path / "input" / "test_video.mp4"
        media_file.parent.mkdir(parents=True)
        media_file.write_bytes(b"fake video content")

        output_dir = tmp_path / "output"

        # Mock provider
        mock_provider = AsyncMock()
        mock_provider.transcribe.return_value = TranscriptResult(
            text="这是测试转录。第一句话。第二句话。",
            language="zh",
            model="mock-model",
            provider="mock",
        )

        config = {
            "transcript": {"language_hint": "zh"},
            "archive": {"enabled": True},
            "analysis": {"enabled": True},
        }

        result = await process_local_file(
            media_file,
            config=config,
            provider=mock_provider,
            output_dir=output_dir,
        )

        assert result["status"] == "success"
        assert result["source_type"] == "local"
        assert "transcript_path" in result
        assert Path(result["transcript_path"]).exists()

        # Check markdown was created
        assert "markdown_path" in result
        md_content = Path(result["markdown_path"]).read_text(encoding="utf-8")
        assert "test_video" in md_content

        # Check analysis was created
        assert "analysis_path" in result
        analysis_data = json.loads(
            Path(result["analysis_path"]).read_text(encoding="utf-8")
        )
        assert analysis_data["source_type"] == "local"
        assert analysis_data["title"] == "test_video"


class TestRunLocalPipeline:
    @pytest.mark.asyncio
    async def test_batch_processing(self, tmp_path):
        # Create fake media files
        files = []
        for i in range(3):
            f = tmp_path / "input" / f"video_{i}.mp4"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(b"fake")
            files.append(f)

        output_dir = tmp_path / "output"

        mock_provider = AsyncMock()
        mock_provider.transcribe.return_value = TranscriptResult(
            text="Transcript text.",
            provider="mock",
        )

        config = {
            "transcript": {"provider": "local", "language_hint": "zh"},
            "archive": {"enabled": True},
            "analysis": {"enabled": True},
        }

        with patch("core.pipeline.create_transcript_provider", return_value=mock_provider):
            result = await run_local_pipeline(
                files, config=config, output_dir=output_dir
            )

        assert result.items_total == 3
        assert result.items_success == 3
        assert len(result.outputs) == 3
