"""Tests for URL parser local file detection."""

import pytest
from pathlib import Path

from core.url_parser import URLParser


class TestURLParserLocal:
    def test_parse_local_mp4(self, tmp_path):
        f = tmp_path / "video.mp4"
        f.write_bytes(b"fake")
        result = URLParser.parse(str(f))
        assert result is not None
        assert result["type"] == "local_file"
        assert len(result["files"]) == 1

    def test_parse_local_directory(self, tmp_path):
        for name in ["a.mp4", "b.mov", "c.txt"]:
            (tmp_path / name).write_bytes(b"fake")
        result = URLParser.parse(str(tmp_path))
        assert result is not None
        assert result["type"] == "local_dir"
        assert len(result["files"]) == 2  # only mp4 and mov

    def test_parse_empty_directory(self, tmp_path):
        (tmp_path / "readme.txt").write_text("not media")
        result = URLParser.parse(str(tmp_path))
        # No media files → falls through to URL parsing → None
        assert result is None

    def test_parse_douyin_url_still_works(self):
        result = URLParser.parse("https://www.douyin.com/video/7123456789")
        assert result is not None
        assert result["type"] == "video"

    def test_parse_user_url_still_works(self):
        result = URLParser.parse("https://www.douyin.com/user/MS4wLjABAAAAtest")
        assert result is not None
        assert result["type"] == "user"
