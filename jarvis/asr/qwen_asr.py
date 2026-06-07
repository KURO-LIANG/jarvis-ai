import time
from dataclasses import dataclass
from pathlib import Path

import requests


class ASRError(Exception):
    """Raised when speech recognition fails."""


@dataclass
class TranscriptionResult:
    text: str


class QwenASR:
    """Calls OMLX POST /v1/audio/transcriptions for speech-to-text."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        api_key: str = "",
        model: str = "Qwen3-ASR-1.7B-8bit",
        timeout: int = 60,
        max_retries: int = 1,
    ) -> None:
        self._endpoint = f"{base_url.rstrip('/')}/v1/audio/transcriptions"
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._max_retries = max_retries

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        """Upload WAV file to OMLX and return transcribed text.

        Raises:
            ASRError: On HTTP error, timeout, or empty response.
        """
        if not audio_path.exists():
            raise ASRError(f"Audio file not found: {audio_path}")

        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                headers = self._build_headers()
                with open(audio_path, "rb") as f:
                    response = requests.post(
                        self._endpoint,
                        files={"file": (audio_path.name, f, "audio/wav")},
                        data={"model": self._model},
                        headers=headers,
                        timeout=self._timeout,
                    )

                if response.status_code == 200:
                    data = response.json()
                    text = data.get("text", "").strip()
                    if not text:
                        raise ASRError("ASR returned empty text.")
                    return TranscriptionResult(text=text)

                if response.status_code >= 500 and attempt < self._max_retries:
                    time.sleep(2**attempt)
                    continue

                raise ASRError(
                    f"ASR request failed (HTTP {response.status_code}): "
                    f"{response.text[:200]}"
                )

            except requests.RequestException as e:
                last_error = e
                if attempt < self._max_retries:
                    time.sleep(2**attempt)
                    continue

        raise ASRError(
            f"ASR request failed after {self._max_retries + 1} attempts"
        ) from last_error

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers
