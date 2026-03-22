"""Tests for analysis manager (JSON summary)."""

import json
import pytest
from pathlib import Path

from core.analysis_manager import AnalysisManager, _extract_short_summary


class TestExtractShortSummary:
    def test_basic_extraction(self):
        text = "第一句。第二句。第三句。第四句。"
        result = _extract_short_summary(text, max_sentences=2)
        assert "第一句。" in result
        assert "第二句。" in result
        assert "第三句。" not in result

    def test_empty_text(self):
        assert _extract_short_summary("") == ""

    def test_error_placeholder(self):
        assert _extract_short_summary("[转录失败]") == ""

    def test_no_punctuation_fallback(self):
        text = "a" * 300
        result = _extract_short_summary(text)
        assert len(result) <= 200


class TestAnalysisManager:
    @pytest.mark.asyncio
    async def test_write_analysis_basic(self, tmp_path):
        mgr = AnalysisManager()
        path = await mgr.write_analysis(
            title="测试视频",
            author="作者",
            source_type="douyin",
            aweme_id="789",
            publish_time="2026-03-22",
            source_url="https://douyin.com/video/789",
            transcript_path="/tmp/test.transcript.txt",
            markdown_path="/tmp/test.md",
            tags=["标签1"],
            transcript_text="第一句话。第二句话。",
            output_dir=tmp_path,
        )
        assert path is not None
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["title"] == "测试视频"
        assert data["author"] == "作者"
        assert data["aweme_id"] == "789"
        assert "第一句话" in data["short_summary"]
        assert data["tags"] == ["标签1"]
        assert "analyzed_at" in data

    @pytest.mark.asyncio
    async def test_write_analysis_local(self, tmp_path):
        mgr = AnalysisManager()
        path = await mgr.write_analysis(
            title="local_video",
            source_type="local",
            transcript_text="Some transcript.",
            output_dir=tmp_path,
        )
        assert path is not None
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["source_type"] == "local"
