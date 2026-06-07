from dataclasses import dataclass, field


@dataclass
class ConversationTurn:
    """A single turn in the conversation."""
    role: str       # "user" | "assistant"
    content: str
    timestamp: float = 0.0


@dataclass
class UserMemory:
    """Long-term memory about the user, persisted across sessions."""

    user_name: str | None = None
    location: str | None = None
    company: str | None = None
    occupation: str | None = None
    interests: list[str] = field(default_factory=list)
    devices: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    preferences: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    updated_at: str = ""  # ISO timestamp
