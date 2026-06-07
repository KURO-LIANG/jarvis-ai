from abc import ABC, abstractmethod

from jarvis.asr.qwen_asr import ASRError, QwenASR
from jarvis.audio.recorder import MicrophoneRecorder, RecordingError


class InputStrategy(ABC):
    """Abstract strategy for acquiring user text input."""

    @abstractmethod
    def get_input(self) -> str:
        """Acquire user input and return it as text.

        Raises:
            RecordingError: On microphone failure.
            ASRError: On speech recognition failure.
        """
        ...


class VoiceInputStrategy(InputStrategy):
    """Acquires input via microphone recording + ASR transcription."""

    def __init__(self, recorder: MicrophoneRecorder, asr: QwenASR) -> None:
        self._recorder = recorder
        self._asr = asr

    def get_input(self) -> str:
        input("Press Enter to start recording...")

        self._recorder.start()
        print("[Recording...] Press Enter to stop.")

        input()

        result = self._recorder.stop()
        print(f"Recorded {result.duration_seconds:.1f}s")

        print("Transcribing...")
        transcription = self._asr.transcribe(result.filepath)
        return transcription.text


class TextInputStrategy(InputStrategy):
    """Acquires input via terminal text entry. Used in debug mode."""

    def get_input(self) -> str:
        return input("You: > ")
