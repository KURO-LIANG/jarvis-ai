from enum import Enum
from typing import Callable


class AssistantState(Enum):
    IDLE = "idle"            # Waiting for wake word, continuously listening
    LISTENING = "listening"  # Active, waiting for user speech
    THINKING = "thinking"    # LLM processing / TTS generating
    SPEAKING = "speaking"    # TTS playback (mic stays active for barge-in)


StateListener = Callable[[AssistantState], None]


class StateMachine:
    """Manages voice assistant state transitions with observer pattern."""

    def __init__(self) -> None:
        self._state = AssistantState.IDLE
        self._listeners: list[StateListener] = []

    @property
    def state(self) -> AssistantState:
        return self._state

    def on_state_change(self, callback: StateListener) -> None:
        """Register a callback(state) for every state transition."""
        self._listeners.append(callback)

    # -- Transitions --

    def wake_word_detected(self) -> None:
        """IDLE -> LISTENING."""
        if self._state == AssistantState.IDLE:
            self._transition_to(AssistantState.LISTENING)

    def start_thinking(self) -> None:
        """LISTENING -> THINKING."""
        if self._state == AssistantState.LISTENING:
            self._transition_to(AssistantState.THINKING)

    def start_speaking(self) -> None:
        """THINKING -> SPEAKING."""
        if self._state == AssistantState.THINKING:
            self._transition_to(AssistantState.SPEAKING)

    def done_speaking(self) -> None:
        """SPEAKING -> LISTENING (playback finished normally)."""
        if self._state == AssistantState.SPEAKING:
            self._transition_to(AssistantState.LISTENING)

    def barge_in(self) -> None:
        """SPEAKING -> LISTENING (user interrupted)."""
        if self._state == AssistantState.SPEAKING:
            self._transition_to(AssistantState.LISTENING)

    def exit_conversation(self) -> None:
        """LISTENING -> IDLE (voice exit command)."""
        if self._state == AssistantState.LISTENING:
            self._transition_to(AssistantState.IDLE)

    def thinking_failed(self) -> None:
        """THINKING -> LISTENING (LLM/TTS error recovery)."""
        if self._state == AssistantState.THINKING:
            self._transition_to(AssistantState.LISTENING)

    def timeout(self) -> None:
        """LISTENING -> IDLE (silence timeout)."""
        if self._state == AssistantState.LISTENING:
            self._transition_to(AssistantState.IDLE)

    # -- State queries --

    def is_idle(self) -> bool:
        return self._state == AssistantState.IDLE

    def is_listening(self) -> bool:
        return self._state == AssistantState.LISTENING

    def is_thinking(self) -> bool:
        return self._state == AssistantState.THINKING

    def is_speaking(self) -> bool:
        return self._state == AssistantState.SPEAKING

    # -- Internal --

    def _transition_to(self, new_state: AssistantState) -> None:
        self._state = new_state
        for listener in self._listeners:
            try:
                listener(new_state)
            except Exception:
                pass
