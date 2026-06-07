class WakeWordDetector:
    """Detects wake word in ASR transcriptions via case-insensitive substring match."""

    def __init__(self, wake_word: str = "jarvis") -> None:
        self._wake_word = wake_word.lower()

    @property
    def wake_word(self) -> str:
        return self._wake_word

    def is_wake_word(self, text: str) -> bool:
        """Check if wake word appears anywhere in the text."""
        return self._wake_word in text.lower()

    def strip_wake_word(self, text: str) -> str:
        """Remove the wake word from the text, returning the actual command.

        Keeps the remainder after the first occurrence of the wake word.
        E.g., "jarvis what time is it" -> "what time is it"
        """
        text_lower = text.lower()
        idx = text_lower.find(self._wake_word)
        if idx == -1:
            return text

        after = text[idx + len(self._wake_word):].strip()
        # Trim leading punctuation
        while after and after[0] in ",.，。；;:：!！?？":
            after = after[1:].strip()
        return after
