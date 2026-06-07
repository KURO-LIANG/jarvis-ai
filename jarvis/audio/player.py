import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Iterator


class PlaybackError(Exception):
    """Raised when audio playback fails."""


class AudioPlayer:
    """Plays audio files using macOS afplay in a background thread.

    Instance methods (play/stop/is_playing/wait) are non-blocking
    and support barge-in. Static methods remain for simple beep playback.
    """

    def __init__(self) -> None:
        self._process: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._playback_done = threading.Event()
        self._playback_done.set()  # start as "done"

    # -- Public instance API --

    def play(self, filepath: Path) -> None:
        """Start non-blocking audio playback in a daemon thread.

        If already playing, stops the current playback first.
        """
        if not filepath.exists():
            raise PlaybackError(f"Audio file not found: {filepath}")

        self.stop()
        self._playback_done.clear()
        self._thread = threading.Thread(
            target=self._play_blocking,
            args=(filepath,),
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Terminate current playback if active. Thread-safe."""
        with self._lock:
            proc = self._process
            self._process = None
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=1)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                try:
                    proc.kill()
                    proc.wait(timeout=1)
                except (ProcessLookupError, Exception):
                    pass
        self._playback_done.set()

    def is_playing(self) -> bool:
        """True if audio is currently playing."""
        with self._lock:
            return self._process is not None and self._process.poll() is None

    def wait(self) -> None:
        """Block until current playback completes."""
        if self._thread is not None and self._thread.is_alive():
            self._thread.join()

    @property
    def playback_done(self) -> threading.Event:
        """Event that is set when playback finishes or is stopped."""
        return self._playback_done

    # -- Private --

    def _play_blocking(self, filepath: Path) -> None:
        """Run afplay in a subprocess. Called from daemon thread."""
        try:
            with self._lock:
                self._process = subprocess.Popen(
                    ["afplay", str(filepath)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                proc = self._process

            returncode = proc.wait()

            with self._lock:
                self._process = None
                if returncode != 0 and returncode != -15:
                    # -15 = SIGTERM from stop(), not an error
                    pass

        except FileNotFoundError:
            with self._lock:
                self._process = None
        finally:
            self._playback_done.set()

    # -- Static methods (unchanged, for beeps) --

    @staticmethod
    def play_file(filepath: Path) -> None:
        """Synchronous playback via afplay. Blocks until complete. For beeps."""
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
    def play_stream(
        audio_chunks: Iterator[bytes], suffix: str = ".wav"
    ) -> None:
        """Synchronous playback of raw audio chunks."""
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
