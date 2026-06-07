from abc import ABC, abstractmethod
from pathlib import Path


class SpeechError(Exception):
    """Raised when speech synthesis fails."""


class SpeechProvider(ABC):
    """Abstract strategy for text-to-speech synthesis."""

    @property
    def audio_format(self) -> str:
        """File extension for the audio output (without dot)."""
        return "wav"

    @abstractmethod
    def synthesize(self, text: str, output_path: Path) -> Path:
        """Convert text to speech and save to output_path.

        Returns the output_path.
        """
        ...
