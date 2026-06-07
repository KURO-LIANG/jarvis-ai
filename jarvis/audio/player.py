import subprocess
import tempfile
from pathlib import Path
from typing import Iterator


class PlaybackError(Exception):
    """Raised when audio playback fails."""


class AudioPlayer:
    """Plays WAV files using macOS afplay."""

    @staticmethod
    def play_file(filepath: Path) -> None:
        """Play a WAV file via afplay. Blocks until playback completes.

        Raises:
            PlaybackError: If afplay fails or the file does not exist.
        """
        if not filepath.exists():
            raise PlaybackError(f"Audio file not found: {filepath}")

        try:
            subprocess.run(
                ["afplay", str(filepath)],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            raise PlaybackError(f"Playback failed: {e.stderr.decode().strip()}") from e
        except FileNotFoundError:
            raise PlaybackError(
                "afplay command not found. Are you running on macOS?"
            ) from None

    @staticmethod
    def play(filepath: Path) -> None:
        """Play a WAV file via afplay. (compatibility alias for play_file)"""
        return AudioPlayer.play_file(filepath)

    @staticmethod
    def play_stream(
        audio_chunks: Iterator[bytes], suffix: str = ".wav"
    ) -> None:
        """Play audio from a stream of raw audio byte chunks.

        Buffers all chunks to a temporary file, then plays via afplay.
        """
        chunks = list(audio_chunks)
        if not chunks:
            raise PlaybackError("No audio chunks received.")

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = Path(tmp.name)
            for chunk in chunks:
                tmp.write(chunk)

        try:
            AudioPlayer.play_file(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)
