"""Tests that archive_record is actually written to the database."""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock

from core.pipeline import process_local_file
from core.transcript_providers.base import TranscriptResult
from storage.database import Database


class _FakeDatabase:
    """Minimal fake that records upsert_archive_record calls."""

    def __init__(self):
        self.archive_records = []

    async def upsert_archive_record(self, record):
        self.archive_records.append(record)


class TestArchiveRecordInLocalPipeline:
    @pytest.mark.asyncio
    async def test_local_file_writes_archive_record(self, tmp_path):
        media_file = tmp_path / "test_video.mp4"
        media_file.write_bytes(b"fake video")
        output_dir = tmp_path / "output"

        mock_provider = AsyncMock()
        mock_provider.transcribe.return_value = TranscriptResult(
            text="转录文本。第一句。",
            provider="mock",
            model="mock-model",
        )

        db = _FakeDatabase()

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
            database=db,
        )

        assert result["status"] == "success"

        # archive_record should have been written
        assert len(db.archive_records) == 1
        record = db.archive_records[0]
        assert record["aweme_id"] == "test_video"
        assert record["source_type"] == "local"
        assert record["markdown_path"] is not None
        assert record["analysis_path"] is not None

    @pytest.mark.asyncio
    async def test_no_db_write_when_database_is_none(self, tmp_path):
        media_file = tmp_path / "test_video.mp4"
        media_file.write_bytes(b"fake video")

        mock_provider = AsyncMock()
        mock_provider.transcribe.return_value = TranscriptResult(
            text="Some text.",
            provider="mock",
        )

        config = {
            "transcript": {"language_hint": "zh"},
            "archive": {"enabled": True},
            "analysis": {"enabled": True},
        }

        # No database — should not crash
        result = await process_local_file(
            media_file,
            config=config,
            provider=mock_provider,
            output_dir=tmp_path / "out",
            database=None,
        )
        assert result["status"] == "success"


class TestArchiveRecordInTranscriptManager:
    @pytest.mark.asyncio
    async def test_transcript_manager_writes_archive_record(self, tmp_path):
        from config import ConfigLoader
        from core.transcript_manager import TranscriptManager
        from storage import FileManager

        config = ConfigLoader()
        config.update(
            transcript={
                "enabled": True,
                "provider": "local",
                "local_model": "tiny",
                "language_hint": "zh",
                "response_formats": ["txt"],
            },
            archive={"enabled": True},
            analysis={"enabled": True},
        )

        file_manager = FileManager(str(tmp_path / "Downloaded"))
        db = _FakeDatabase()
        # Also need upsert_transcript_job
        db.upsert_transcript_job = AsyncMock()

        manager = TranscriptManager(config, file_manager, database=db)

        # Mock the provider
        mock_provider = AsyncMock()
        mock_provider.transcribe.return_value = TranscriptResult(
            text="测试转录内容。",
            provider="mock",
            model="mock",
        )
        mock_provider.name = "mock"
        mock_provider.is_available.return_value = True
        manager._provider = mock_provider

        video_path = tmp_path / "Downloaded" / "author" / "post" / "demo.mp4"
        video_path.parent.mkdir(parents=True, exist_ok=True)
        video_path.write_bytes(b"video data")

        result = await manager.process_video(
            video_path,
            aweme_id="999",
            title="测试视频",
            author="作者",
            publish_date="2026-03-22",
        )

        assert result["status"] == "success"
        assert len(db.archive_records) == 1
        record = db.archive_records[0]
        assert record["aweme_id"] == "999"
        assert record["source_type"] == "douyin"
        assert record["markdown_path"] is not None
