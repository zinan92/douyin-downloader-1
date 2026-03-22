"""Tests for transcript formatting."""

from core.transcript_formatter import format_transcript, _group_into_paragraphs


class TestFormatTranscript:
    def test_empty_string(self):
        assert format_transcript("") == ""

    def test_error_placeholder_passthrough(self):
        assert format_transcript("[转录失败]") == "[转录失败]"

    def test_preserves_existing_paragraphs(self):
        text = "First paragraph.\n\nSecond paragraph."
        result = format_transcript(text)
        assert result == "First paragraph.\n\nSecond paragraph."

    def test_splits_on_chinese_punctuation(self):
        text = "第一句。第二句。第三句。第四句。第五句。第六句。"
        result = format_transcript(text)
        assert "\n\n" in result
        paragraphs = result.split("\n\n")
        assert len(paragraphs) == 2

    def test_splits_on_english_punctuation(self):
        sentences = [f"Sentence {i}." for i in range(1, 11)]
        text = " ".join(sentences)
        result = format_transcript(text)
        assert "\n\n" in result

    def test_long_text_comma_fallback(self):
        # Over 200 chars, no sentence-ending punctuation, has commas
        text = "，".join(f"片段{i}" for i in range(50))
        result = format_transcript(text)
        assert "\n\n" in result

    def test_short_text_no_splitting(self):
        text = "这是一句短话"
        result = format_transcript(text)
        assert result == "这是一句短话"


class TestGroupIntoParagraphs:
    def test_basic_grouping(self):
        segments = ["a", "b", "c", "d", "e", "f"]
        result = _group_into_paragraphs(segments, group_size=3)
        assert result == "abc\n\ndef"

    def test_uneven_grouping(self):
        segments = ["a", "b", "c", "d"]
        result = _group_into_paragraphs(segments, group_size=3)
        paragraphs = result.split("\n\n")
        assert len(paragraphs) == 2
