from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ConversationResult:
    text: str | None  # None when the provider handles reply internally
    audio_path: Path


class ConversationProvider(ABC):
    """Abstract strategy for generating a spoken reply from user text."""

    @abstractmethod
    def respond(self, user_text: str) -> ConversationResult:
        """Generate a spoken reply. Returns text (if known) and audio path."""
        ...
