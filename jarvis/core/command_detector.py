class CommandDetector:
    """Checks user speech for exit and interrupt commands via case-insensitive
    substring match.
    """

    def __init__(
        self,
        exit_commands: list[str],
        interrupt_commands: list[str] | None = None,
    ) -> None:
        self._exit_cmds = [c.lower() for c in exit_commands]
        self._interrupt_cmds = (
            [c.lower() for c in interrupt_commands]
            if interrupt_commands
            else []
        )

    def is_exit_command(self, text: str) -> bool:
        """True if text contains any exit command phrase."""
        t = text.lower()
        return any(cmd in t for cmd in self._exit_cmds)

    def is_interrupt_command(self, text: str) -> bool:
        """True if text contains any interrupt (barge-in) command phrase."""
        t = text.lower()
        return any(cmd in t for cmd in self._interrupt_cmds)
