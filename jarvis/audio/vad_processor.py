import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf
import webrtcvad


@dataclass
class SpeechSegment:
    """A detected speech utterance, saved as a WAV file."""

    audio_path: Path
    duration_seconds: float
    timestamp: float  # time.time() when segment completed


class VadProcessor:
    """Consumes audio chunks, detects speech vs silence, emits complete
    speech segments as WAV files for ASR transcription.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        vad_aggressiveness: int = 2,
        frame_ms: int = 30,
        silence_threshold_ms: int = 800,
        min_speech_ms: int = 300,
    ) -> None:
        if frame_ms not in (10, 20, 30):
            raise ValueError("frame_ms must be 10, 20, or 30")

        self._sample_rate = sample_rate
        self._frame_ms = frame_ms
        self._silence_frames = max(1, silence_threshold_ms // frame_ms)
        self._min_speech_frames = max(1, min_speech_ms // frame_ms)

        self._vad = webrtcvad.Vad(vad_aggressiveness)
        self._speech_buffer: list[np.ndarray] = []
        self._silence_count: int = 0
        self._is_speaking: bool = False
        self._segment_count: int = 0

    def process_frame(self, frame: np.ndarray) -> SpeechSegment | None:
        """Process a single audio frame (int16, shape matches blocksize).

        Returns a SpeechSegment when a complete utterance ends,
        or None if still in progress / silent.
        """
        frame_bytes = frame.tobytes()
        is_speech = self._vad.is_speech(frame_bytes, self._sample_rate)

        if is_speech:
            self._speech_buffer.append(frame)
            self._silence_count = 0
            self._is_speaking = True
        elif self._is_speaking:
            self._silence_count += 1
            self._speech_buffer.append(frame)
            if self._silence_count >= self._silence_frames:
                return self._finalize_segment()

        return None

    def flush(self) -> SpeechSegment | None:
        """Force-finalize any in-progress speech (e.g., on timeout)."""
        if self._is_speaking and len(self._speech_buffer) >= self._min_speech_frames:
            return self._finalize_segment()
        self._reset()
        return None

    def _finalize_segment(self) -> SpeechSegment | None:
        """Write accumulated speech frames to WAV, return SpeechSegment."""
        if len(self._speech_buffer) < self._min_speech_frames:
            self._reset()
            return None

        audio = np.concatenate(self._speech_buffer, axis=0)
        duration = len(audio) / self._sample_rate

        output_path = Path(f"/tmp/jarvis_segment_{self._segment_count}.wav")
        self._segment_count += 1
        sf.write(str(output_path), audio, self._sample_rate)

        timestamp = time.time()
        self._reset()
        return SpeechSegment(
            audio_path=output_path,
            duration_seconds=round(duration, 2),
            timestamp=timestamp,
        )

    def _reset(self) -> None:
        """Reset internal state for the next utterance."""
        self._speech_buffer = []
        self._silence_count = 0
        self._is_speaking = False
