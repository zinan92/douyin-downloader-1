"""Tests for transcript provider abstraction."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.transcript_providers.base import TranscriptProvider, TranscriptResult
from core.transcript_providers.local_whisper_provider import LocalWhisperProvider
from core.transcript_providers.openai_provider import OpenAITranscriptProvider


class TestTranscriptResult:
    def test_success_when_text_present(self):
        r = TranscriptResult(text="Hello world", provider="test")
        assert r.success is True

    def test_failure_when_empty(self):
        r = TranscriptResult(text="", provider="test")
        assert r.success is False

    def test_failure_when_error_prefix(self):
        r = TranscriptResult(text="[转录失败]", provider="test")
        assert r.success is False

    def test_immutable(self):
        r = TranscriptResult(text="Hello", provider="test")
        with pytest.raises(AttributeError):
            r.text = "Mutated"


class TestLocalWhisperProvider:
    def test_name(self):
        provider = LocalWhisperProvider()
        assert provider.name == "local_whisper"

    def test_is_available_no_deps(self):
        provider = LocalWhisperProvider()
        provider._mlx_available = False
        provider._cli_available = False
        assert provider.is_available() is False

    def test_is_available_with_cli(self):
        provider = LocalWhisperProvider()
        provider._mlx_available = False
        provider._cli_available = True
        assert provider.is_available() is True

    @pytest.mark.asyncio
    async def test_transcribe_no_deps(self, tmp_path):
        provider = LocalWhisperProvider()
        provider._mlx_available = False
        provider._cli_available = False

        dummy_file = tmp_path / "test.mp4"
        dummy_file.write_bytes(b"fake video data")

        result = await provider.transcribe(dummy_file)
        assert result.success is False
        assert "未安装" in result.text


class TestOpenAITranscriptProvider:
    def test_name(self):
        provider = OpenAITranscriptProvider({})
        assert provider.name == "openai_api"

    def test_is_available_no_key(self):
        provider = OpenAITranscriptProvider({})
        assert provider.is_available() is False

    def test_is_available_with_key(self):
        provider = OpenAITranscriptProvider({"api_key": "sk-test"})
        assert provider.is_available() is True

    def test_is_available_with_env_key(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-test")
        provider = OpenAITranscriptProvider({"api_key_env": "OPENAI_API_KEY"})
        assert provider.is_available() is True

    @pytest.mark.asyncio
    async def test_transcribe_missing_key(self, tmp_path):
        provider = OpenAITranscriptProvider({})
        dummy_file = tmp_path / "test.mp4"
        dummy_file.write_bytes(b"fake")

        result = await provider.transcribe(dummy_file)
        assert result.success is False
        assert "API key" in result.text
