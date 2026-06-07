class CommandDetector:
    """Checks user speech for exit commands via case-insensitive substring match."""

    def __init__(self, exit_commands: list[str]) -> None:
        self._exit_cmds = [c.lower() for c in exit_commands]

    def is_exit_command(self, text: str) -> bool:
        """True if text contains any exit command phrase."""
        t = text.lower()
        return any(cmd in t for cmd in self._exit_cmds)
