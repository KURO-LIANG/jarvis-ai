import json
from pathlib import Path


class FileStorage:
    """JSON file persistence for user memory."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> dict | None:
        """Load memory from disk. Returns None if file doesn't exist."""
        if not self._path.exists():
            return None
        try:
            return json.loads(self._path.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def save(self, data: dict) -> None:
        """Save memory to disk. Creates parent directories if needed."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            "utf-8",
        )
