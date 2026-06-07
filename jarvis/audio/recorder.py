import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf


class RecordingError(Exception):
    """Raised when microphone recording fails."""


@dataclass
class RecordingResult:
    filepath: Path
    duration_seconds: float
    sample_rate: int


class MicrophoneRecorder:
    """Push-to-talk recorder using sounddevice InputStream.

    Records audio from the default microphone into memory chunks.
    Start/stop are controlled externally (via keyboard input in the orchestrator).
    """

    def __init__(self, sample_rate: int = 16000, channels: int = 1) -> None:
        self._sample_rate = sample_rate
        self._channels = channels
        self._stream: sd.InputStream | None = None
        self._chunks: list[np.ndarray] = []
        self._recording = False

    def start(self) -> None:
        """Begin capturing audio from the default microphone."""
        self._chunks = []
        self._recording = True
        try:
            self._stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype="int16",
                callback=self._callback,
            )
            self._stream.start()
        except sd.PortAudioError as e:
            self._recording = False
            raise RecordingError(
                "Failed to access microphone. Check System Preferences > "
                "Security & Privacy > Microphone permissions."
            ) from e

    def stop(self) -> RecordingResult:
        """Stop recording, concatenate chunks, write WAV file, and return result."""
        self._recording = False

        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if not self._chunks:
            raise RecordingError("No audio data captured.")

        audio_data = np.concatenate(self._chunks, axis=0)
        duration = len(audio_data) / self._sample_rate

        output_path = Path("input.wav")
        sf.write(str(output_path), audio_data, self._sample_rate)

        return RecordingResult(
            filepath=output_path,
            duration_seconds=round(duration, 2),
            sample_rate=self._sample_rate,
        )

    def _callback(
        self,
        indata: np.ndarray,
        frames: int,
        time: sd.CallbackStop | None,
        status: sd.CallbackFlags,
    ) -> None:
        """sounddevice callback: append chunk if recording is active."""
        if status:
            return
        if self._recording:
            self._chunks.append(indata.copy())
