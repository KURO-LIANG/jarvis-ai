import queue
import threading

import numpy as np
import sounddevice as sd


class MicStreamError(Exception):
    """Raised when microphone stream operations fail."""


class ContinuousMicStream:
    """Always-on microphone stream feeding a thread-safe queue.

    Audio chunks (numpy int16 arrays) are produced by the sounddevice
    callback and consumed by another thread for VAD/ASR processing.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        blocksize: int = 480,  # 30ms at 16kHz
        queue_size: int = 200,  # ~6s buffer at 30ms frames
    ) -> None:
        self._sample_rate = sample_rate
        self._channels = channels
        self._blocksize = blocksize
        self._queue: queue.Queue[np.ndarray | None] = queue.Queue(maxsize=queue_size)
        self._stream: sd.InputStream | None = None
        self._active = threading.Event()
        self._paused = threading.Event()

    @property
    def is_active(self) -> bool:
        return self._active.is_set()

    @property
    def is_paused(self) -> bool:
        return self._paused.is_set()

    def start(self) -> None:
        """Open and start the input stream."""
        self._active.set()
        self._paused.clear()
        try:
            self._stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype="int16",
                blocksize=self._blocksize,
                callback=self._callback,
            )
            self._stream.start()
        except sd.PortAudioError as e:
            self._active.clear()
            raise MicStreamError(
                "Failed to access microphone. Check System Preferences > "
                "Security & Privacy > Microphone permissions."
            ) from e

    def stop(self) -> None:
        """Stop and close the stream. Sends sentinel None to queue."""
        self._active.clear()
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass

    def pause(self) -> None:
        """Pause delivery of chunks to the queue (for SPEAKING state)."""
        self._paused.set()

    def resume(self) -> None:
        """Resume delivery of chunks to the queue."""
        self._paused.clear()

    def get_chunk(self, timeout: float = 0.5) -> np.ndarray | None:
        """Blocking get of the next audio chunk.

        Returns None sentinel when stream stops, or on timeout
        (which signals the caller to check for state changes).
        """
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def drain(self) -> None:
        """Discard all pending chunks in the queue."""
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def _callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        """sounddevice callback. Runs on a real-time audio thread, never blocks."""
        if status:
            return
        if not self._active.is_set():
            return
        if self._paused.is_set():
            return
        try:
            self._queue.put_nowait(indata.copy())
        except queue.Full:
            pass  # drop frame if consumer is too slow
