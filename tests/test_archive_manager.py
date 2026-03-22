"""Tests for archive manager (markdown output)."""

import pytest
from pathlib import Path

from core.archive_manager import ArchiveManager, _safe_filename


class TestSafeFilename:
    def test_removes_special_chars(self):
        assert "/" not in _safe_filename("hello/world")
        assert ":" not in _safe_filename("foo:bar")
        assert "\n" not in _safe_filename("line1\nline2")

    def test_truncates(self):
        long_name = "a" * 200
        assert len(_safe_filename(long_name, max_len=80)) <= 80

    def test_empty_fallback(self):
        assert _safe_filename("") == "untitled"


class TestArchiveManager:
    @pytest.mark.asyncio
    async def test_write_markdown_basic(self, tmp_path):
        mgr = ArchiveManager()
        path = await mgr.write_markdown(
            title="测试视频",
            transcript_text="这是转录文本。第一段内容。",
            output_dir=tmp_path,
            aweme_id="123456",
            source_url="https://douyin.com/video/123456",
            author="测试作者",
            publish_date="2026-03-22",
            tags=["测试", "视频"],
        )
        assert path is not None
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "# 测试视频" in content
        assert "测试作者" in content
        assert "2026-03-22" in content
        assert "#测试" in content
        assert "这是转录文本" in content

    @pytest.mark.asyncio
    async def test_write_markdown_local_source(self, tmp_path):
        mgr = ArchiveManager()
        path = await mgr.write_markdown(
            title="本地视频",
            transcript_text="Hello world.",
            output_dir=tmp_path,
            source_type="local",
        )
        assert path is not None
        content = path.read_text(encoding="utf-8")
        assert "本地文件" in content

    @pytest.mark.asyncio
    async def test_resolve_output_dir_custom(self, tmp_path):
        mgr = ArchiveManager(output_dir=str(tmp_path / "custom"))
        result = mgr.resolve_output_dir(tmp_path / "fallback")
        assert result == tmp_path / "custom"

    @pytest.mark.asyncio
    async def test_resolve_output_dir_fallback(self, tmp_path):
        mgr = ArchiveManager()
        result = mgr.resolve_output_dir(tmp_path / "fallback")
        assert result == tmp_path / "fallback"
