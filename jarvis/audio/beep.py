import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf


class BeepGenerator:
    """Generates notification beeps as temporary WAV files."""

    SAMPLE_RATE = 16000

    @staticmethod
    def wake_beep() -> Path:
        """Two quick ascending tones (~0.3s total)."""
        tone1 = BeepGenerator._generate_tone(800, 0.1, 0.5)
        gap = np.zeros(int(BeepGenerator.SAMPLE_RATE * 0.05), dtype=np.int16)
        tone2 = BeepGenerator._generate_tone(1200, 0.15, 0.5)
        samples = np.concatenate([tone1, gap, tone2])
        return BeepGenerator._write_temp_wav(samples)

    @staticmethod
    def timeout_beep() -> Path:
        """Descending tone (~0.35s total)."""
        sr = BeepGenerator.SAMPLE_RATE
        duration = 0.35
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        freq = np.linspace(600, 400, len(t))
        phase = 2 * np.pi * np.cumsum(freq) / sr
        samples = (0.5 * 32767 * np.sin(phase)).astype(np.int16)
        return BeepGenerator._write_temp_wav(samples)

    @staticmethod
    def _generate_tone(
        frequency: float,
        duration_seconds: float,
        amplitude: float = 0.5,
    ) -> np.ndarray:
        """Generate a sine wave tone as int16 samples."""
        sr = BeepGenerator.SAMPLE_RATE
        t = np.linspace(0, duration_seconds, int(sr * duration_seconds), endpoint=False)
        samples = (amplitude * 32767 * np.sin(2 * np.pi * frequency * t)).astype(np.int16)
        return samples

    @staticmethod
    def _write_temp_wav(samples: np.ndarray) -> Path:
        """Write samples to a temporary WAV file, return path."""
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_path = Path(tmp.name)
        sf.write(str(tmp_path), samples, BeepGenerator.SAMPLE_RATE)
        return tmp_path
