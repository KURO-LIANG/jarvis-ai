from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Message:
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class ChatResponse:
    content: str
    model: str = ""
    usage: dict | None = None


class LLMError(Exception):
    """Raised when LLM call fails."""


class LLMProvider(ABC):
    """Abstract interface for LLM backends."""

    @abstractmethod
    def chat(
        self,
        messages: list[Message],
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> ChatResponse:
        """Send messages to the LLM and return the response."""
        ...
