class WakeWordDetector:
    """Detects wake words via strict exact/prefix match.

    Only words listed in the config can trigger wake-up.
    No substring, fuzzy, or phonetic similarity matching.

    Examples with wake_words=["jarvis", "javis"]:
      "jarvis"       -> True  (exact)
      "Jarvis"       -> True  (case-insensitive)
      "jarvis hello" -> True  (prefix + separator)
      "Jobs"         -> False
      "Java"         -> False
      "já ves"       -> False
    """

    def __init__(self, wake_words: list[str]) -> None:
        self._wake_words = [w.lower() for w in wake_words]

    @property
    def wake_words(self) -> list[str]:
        return list(self._wake_words)

    def is_wake_word(self, text: str) -> bool:
        """Strict match: normalized text must equal or start with a wake word
        followed by a word boundary (separator or end-of-string)."""
        t = text.lower().strip()
        for w in self._wake_words:
            if t == w:
                return True
            if t.startswith(w) and (
                len(t) == len(w) or t[len(w)] in " ,.，。；;:：!！?？"
            ):
                return True
        return False

    def strip_wake_word(self, text: str) -> str:
        """Remove the leading wake word from text, returning the command part.

        E.g., "jarvis what time is it" -> "what time is it"
        """
        t = text.lower().strip()
        for w in self._wake_words:
            if t.startswith(w) and (
                len(t) == len(w) or t[len(w)] in " ,.，。；;:：!！?？"
            ):
                after = text[len(w):].strip(" ,.，。；;:：!！?？")
                return after
        return text
