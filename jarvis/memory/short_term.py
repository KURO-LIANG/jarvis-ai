import time

from jarvis.memory.models import ConversationTurn


class ShortTermMemory:
    """Ring buffer of recent conversation turns."""

    def __init__(self, max_turns: int = 10) -> None:
        self._max_turns = max_turns
        self._turns: list[ConversationTurn] = []

    def add_turn(self, turn: ConversationTurn) -> None:
        """Add a turn and trim to max_turns."""
        if not turn.timestamp:
            turn.timestamp = time.time()
        self._turns.append(turn)
        self._trim()

    def add_exchange(self, user_text: str, assistant_text: str) -> None:
        """Add a user+assistant exchange (2 turns)."""
        now = time.time()
        self._turns.append(ConversationTurn(
            role="user", content=user_text, timestamp=now,
        ))
        self._turns.append(ConversationTurn(
            role="assistant", content=assistant_text, timestamp=now,
        ))
        self._trim()

    def get_turns(self) -> list[ConversationTurn]:
        return list(self._turns)

    def clear(self) -> None:
        self._turns.clear()

    def _trim(self) -> None:
        max_entries = self._max_turns * 2  # each turn = user + assistant
        if len(self._turns) > max_entries:
            self._turns = self._turns[-max_entries:]
