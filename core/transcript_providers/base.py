from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class TranscriptResult:
    """Immutable result from a transcript provider."""

    text: str
    language: str = ""
    model: str = ""
    provider: str = ""
    segments: list = field(default_factory=list)

    @property
    def success(self) -> bool:
        return bool(self.text) and not self.text.startswith("[")


class TranscriptProvider(ABC):
    """Abstract base for transcript providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier used in config and logs."""
        ...

    @abstractmethod
    async def transcribe(
        self,
        media_path: Path,
        *,
        language: str = "zh",
        model: str = "",
    ) -> TranscriptResult:
        """Transcribe a media file and return the result."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether this provider can run (dependencies installed, keys present, etc.)."""
        ...
