from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SpeechSegment:
    """A detected speech utterance, saved as a WAV file."""

    audio_path: Path
    duration_seconds: float
    timestamp: float  # time.time() when segment completed


class VadProvider(ABC):
    """Abstract provider for Voice Activity Detection.

    Consumes audio frames, detects speech vs silence, emits complete
    speech segments as WAV files for ASR transcription.
    """

    @abstractmethod
    def process_frame(self, frame) -> SpeechSegment | None:
        """Process a single audio frame. Returns SpeechSegment when a complete
        utterance ends, or None if still in progress / silent.
        """
        ...

    @abstractmethod
    def flush(self) -> SpeechSegment | None:
        """Force-finalize any in-progress speech (e.g., on timeout)."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset internal state for the next utterance."""
        ...
