import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from jarvis.vad.base import SpeechSegment, VadProvider


class SileroVadProvider(VadProvider):
    """Voice Activity Detection using Silero VAD neural network model.

    Uses silero-vad's pre-trained ONNX model which requires **exactly 512
    samples** per call at 16kHz. Incoming audio frames of arbitrary size are
    buffered internally and processed in 512-sample chunks.

    State machine: silence → speech (>=min_speech_ms) → silence (>=silence_ms) → segment.
    """

    _FRAME_SIZE = 512  # Silero VAD ONNX model fixed input size at 16kHz

    def __init__(
        self,
        sample_rate: int = 16000,
        threshold: float = 0.5,
        min_speech_ms: int = 300,
        silence_ms: int = 800,
    ) -> None:
        self._sample_rate = sample_rate
        self._threshold = threshold
        self._frame_ms = self._FRAME_SIZE / sample_rate * 1000  # ms per VAD frame
        self._min_speech_frames = max(1, round(min_speech_ms / self._frame_ms))
        self._silence_ms = silence_ms

        # Lazy-load model on first use
        self._model = None

        # Buffering: accumulate arbitrary-size mic chunks → exact 512-sample frames
        self._sample_buffer: np.ndarray | None = None  # residual samples (int16)

        self._speech_buffer: list[np.ndarray] = []  # int16 frames for segment output
        self._is_speaking: bool = False
        self._speech_duration_ms: int = 0
        self._silence_duration_ms: int = 0
        self._segment_count: int = 0

    def _ensure_model(self):
        if self._model is not None:
            return
        import silero_vad
        self._model = silero_vad.load_silero_vad(onnx=True)

    def process_frame(self, frame: np.ndarray) -> SpeechSegment | None:
        """Process an int16 audio frame of any length.

        Frames are buffered internally and fed to Silero VAD in exactly
        512-sample chunks. Returns SpeechSegment when an utterance ends.
        """
        self._ensure_model()

        # --- Buffer incoming samples ---
        if frame.ndim == 2:
            frame = frame.flatten()
        if self._sample_buffer is not None:
            frame = np.concatenate([self._sample_buffer, frame])
            self._sample_buffer = None

        # --- Process complete 512-sample frames ---
        result: SpeechSegment | None = None
        offset = 0
        while offset + self._FRAME_SIZE <= len(frame):
            chunk = frame[offset:offset + self._FRAME_SIZE]
            offset += self._FRAME_SIZE

            # Convert int16 → float32 normalized to [-1, 1]
            if chunk.dtype == np.int16:
                audio_float = chunk.astype(np.float32) / 32768.0
            else:
                audio_float = chunk.astype(np.float32)

            # Get speech probability
            with torch.no_grad():
                speech_prob = self._model(
                    torch.from_numpy(audio_float),
                    self._sample_rate,
                ).item()

            # State machine
            if speech_prob >= self._threshold:
                self._speech_buffer.append(chunk)
                self._is_speaking = True
                self._speech_duration_ms += self._frame_ms
                self._silence_duration_ms = 0
            elif self._is_speaking:
                self._silence_duration_ms += self._frame_ms
                self._speech_buffer.append(chunk)
                if self._silence_duration_ms >= self._silence_ms:
                    result = self._finalize_segment()

        # --- Save residual samples for next call ---
        if offset < len(frame):
            self._sample_buffer = frame[offset:].copy()

        return result

    def flush(self) -> SpeechSegment | None:
        """Force-finalize in-progress speech."""
        if self._is_speaking and len(self._speech_buffer) >= self._min_speech_frames:
            return self._finalize_segment()
        self.reset()
        return None

    def reset(self) -> None:
        self._sample_buffer = None
        self._speech_buffer = []
        self._is_speaking = False
        self._speech_duration_ms = 0
        self._silence_duration_ms = 0

    def _finalize_segment(self) -> SpeechSegment | None:
        if len(self._speech_buffer) < self._min_speech_frames:
            self.reset()
            return None

        audio = np.concatenate(self._speech_buffer, axis=0)
        duration = len(audio) / self._sample_rate

        output_path = Path(f"/tmp/jarvis_segment_{self._segment_count}.wav")
        self._segment_count += 1
        sf.write(str(output_path), audio, self._sample_rate)

        timestamp = time.time()
        self.reset()
        return SpeechSegment(
            audio_path=output_path,
            duration_seconds=round(duration, 2),
            timestamp=timestamp,
        )
