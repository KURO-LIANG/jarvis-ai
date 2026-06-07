from pathlib import Path

from jarvis.llm.base import LLMProvider, Message
from jarvis.memory.extractor import MemoryExtractor
from jarvis.memory.models import ConversationTurn
from jarvis.memory.short_term import ShortTermMemory
from jarvis.memory.storage import FileStorage
from jarvis.memory.summary import SummaryMemory


class MemoryManager:
    """Orchestrates short-term and long-term memory."""

    def __init__(
        self,
        max_turns: int,
        storage_path: Path,
        llm: LLMProvider,
        auto_extract: bool = True,
    ) -> None:
        self._short_term = ShortTermMemory(max_turns)
        self._summary = SummaryMemory(FileStorage(storage_path))
        self._extractor = MemoryExtractor(llm)
        self._auto_extract = auto_extract

    # ─── lifecycle ────────────────────────────────────────

    def load(self) -> None:
        self._summary.load()
        if not self._summary.is_empty():
            print("[Memory] Loaded existing user memory")
            # Print summary
            for line in self._summary.build_prompt().split("\n"):
                if line.strip() and line.strip() not in ("=== USER MEMORY ===", "=== END MEMORY ==="):
                    print(f"  {line.strip()}")
            print()

    # ─── turn management ──────────────────────────────────

    def save_turn(self, user_text: str, assistant_text: str) -> None:
        self._short_term.add_exchange(user_text, assistant_text)

    def extract_and_update(self, user_text: str, assistant_text: str) -> None:
        if not self._auto_extract:
            return
        try:
            info = self._extractor.extract(user_text, assistant_text)
        except Exception as e:
            print(f"[Memory] Extraction error: {e}")
            return
        if info:
            changed = self._summary.merge(info)
            if changed:
                print("[Memory] Updated user memory")

    # ─── context building ─────────────────────────────────

    def get_recent_messages(self) -> list[Message]:
        """Recent conversation turns as LLM Message objects."""
        return [
            Message(role=t.role, content=t.content)
            for t in self._short_term.get_turns()
        ]

    def build_context(self) -> str:
        """Long-term memory block for system prompt."""
        return self._summary.build_prompt()
