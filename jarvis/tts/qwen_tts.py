import time
from pathlib import Path

import requests

from jarvis.config import settings


class TTSError(Exception):
    """Raised when text-to-speech synthesis fails."""


class QwenTTS:
    """Calls OMLX POST /v1/audio/speech for text-to-speech.

    The OMLX server returns audio bytes in WAV format.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        api_key: str = "",
        model: str = "Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit",
        voice: str = "Vivian",
        timeout: int = 60,
        max_retries: int = 1,
    ) -> None:
        self._endpoint = f"{base_url.rstrip('/')}/v1/audio/speech"
        self._api_key = api_key
        self._model = model
        self._voice = voice
        self._timeout = timeout
        self._max_retries = max_retries

    def synthesize(self, text: str, output_path: Path) -> None:
        """Convert text to speech and save audio to output_path.

        Raises:
            TTSError: On HTTP error, timeout, or empty response body.
        """
        payload = {
            "model": self._model,
            "input": text,
            "voice": self._voice,
        }

        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                headers = self._build_headers()
                if settings.debug_mode:
                    self._print_request(text)
                response = requests.post(
                    self._endpoint,
                    json=payload,
                    headers=headers,
                    timeout=self._timeout,
                )

                if response.status_code == 200:
                    audio_bytes = response.content
                    if not audio_bytes:
                        raise TTSError("TTS returned empty audio.")
                    output_path.write_bytes(audio_bytes)
                    if settings.debug_mode:
                        self._print_response(len(audio_bytes))
                    return

                if response.status_code >= 500 and attempt < self._max_retries:
                    time.sleep(2**attempt)
                    continue

                raise TTSError(
                    f"TTS request failed (HTTP {response.status_code}): "
                    f"{response.text[:200]}"
                )

            except requests.RequestException as e:
                last_error = e
                if attempt < self._max_retries:
                    time.sleep(2**attempt)
                    continue

        raise TTSError(
            f"TTS request failed after {self._max_retries + 1} attempts"
        ) from last_error

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _print_request(self, text: str) -> None:
        input_preview = text[:100]
        print(f"[TTS Request]")
        print(f"  URL:      {self._endpoint}")
        print(f"  Model:    {self._model}")
        print(f"  Voice:    {self._voice}")
        print(f"  Input:    {input_preview}")
        print()

    @staticmethod
    def _print_response(audio_size: int) -> None:
        print(f"[TTS Response] status=200, audio_bytes={audio_size}")
        print()
