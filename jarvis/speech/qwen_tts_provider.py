from pathlib import Path

from jarvis.config import settings
from jarvis.speech.base import SpeechProvider
from jarvis.tts.qwen_tts import QwenTTS


class QwenSpeechProvider(SpeechProvider):
    """Speech provider backed by local OMLX Qwen3-TTS server."""

    @property
    def audio_format(self) -> str:
        return "wav"

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        api_key: str = "",
        model: str = "Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit",
        voice: str = "Vivian",
        timeout: int = 60,
        max_retries: int = 1,
    ) -> None:
        if settings.debug_mode:
            print(f"[Speech Provider] QwenSpeechProvider")
            print(f"  Model: {model}")
            print(f"  Voice: {voice}")
            print()
        self._tts = QwenTTS(
            base_url=base_url,
            api_key=api_key,
            model=model,
            voice=voice,
            timeout=timeout,
            max_retries=max_retries,
        )

    def synthesize(self, text: str, output_path: Path) -> Path:
        self._tts.synthesize(text, output_path)
        return output_path
