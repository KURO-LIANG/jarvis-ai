import json
import time
from pathlib import Path
from typing import Iterator

import requests

from jarvis.config import settings
from jarvis.speech.base import SpeechError, SpeechProvider


class MiniMaxSpeechProvider(SpeechProvider):
    """Speech provider backed by MiniMax T2A v2 API.

    Supports both streaming (SSE) and non-streaming modes.
    """

    @property
    def audio_format(self) -> str:
        return self._audio_setting["format"]

    def __init__(
        self,
        api_key: str,
        url: str = "https://api.minimaxi.com/v1/t2a_v2",
        model: str = "speech-2.8-turbo",
        mode: str = "stream",
        voice_setting: dict | None = None,
        audio_setting: dict | None = None,
        timeout: int = 60,
        max_retries: int = 1,
    ) -> None:
        self._endpoint = url
        self._api_key = api_key
        self._model = model
        self._mode = mode
        self._voice_setting = voice_setting or {
            "voice_id": "male-qn-qingse",
            "speed": 1,
            "vol": 1,
            "pitch": 0,
            "emotion": "happy",
        }
        self._audio_setting = audio_setting or {
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3",
            "channel": 1,
        }
        self._timeout = timeout
        self._max_retries = max_retries

        if settings.debug_mode:
            print(f"[Speech Provider] MiniMaxSpeechProvider")
            print(f"  Model:    {model}")
            print(f"  Mode:     {mode}")
            print(f"  Voice:    {self._voice_setting['voice_id']}")
            print(f"  Format:   {self._audio_setting['format']}")
            print()

    def synthesize(self, text: str, output_path: Path) -> Path:
        if self._mode == "stream":
            # MiniMax T2A streaming sends cumulative chunks — each new chunk
            # contains all audio from the start. Only keep the final chunk.
            if settings.debug_mode:
                print(f"[TTS Stream] Starting: \"{text[:60]}{'...' if len(text) > 60 else ''}\"")
            audio_bytes = b""
            for chunk in self.synthesize_stream(text):
                audio_bytes = chunk
            output_path.write_bytes(audio_bytes)
            return output_path

        return self._synthesize_normal(text, output_path)

    def synthesize_stream(self, text: str) -> Iterator[bytes]:
        """Stream audio chunks via SSE from MiniMax T2A v2 API.

        Yields raw audio bytes as they arrive.
        """
        payload = self._build_payload(text, stream=True)

        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                headers = self._build_headers()
                if settings.debug_mode:
                    self._print_request(text, stream=True)

                response = requests.post(
                    self._endpoint,
                    json=payload,
                    headers=headers,
                    timeout=self._timeout,
                    stream=True,
                )

                if response.status_code != 200:
                    if response.status_code >= 500 and attempt < self._max_retries:
                        time.sleep(2 ** attempt)
                        continue
                    raise SpeechError(
                        f"MiniMax T2A request failed (HTTP {response.status_code}): "
                        f"{response.text[:200]}"
                    )

                total_bytes = 0
                chunk_count = 0
                for line in response.iter_lines():
                    if not line:
                        continue
                    line_str = line.decode("utf-8").strip()
                    if not line_str.startswith("data:"):
                        continue

                    data_json = line_str[5:].strip()
                    try:
                        data = json.loads(data_json)
                    except json.JSONDecodeError:
                        continue

                    audio_hex = data.get("data", {}).get("audio", "")
                    status = data.get("data", {}).get("status", 0)

                    if audio_hex:
                        try:
                            chunk = self._decode_audio_hex(audio_hex)
                        except Exception:
                            print(f"[TTS Warning] hex decode failed, "
                                  f"raw preview: {audio_hex[:80]}...")
                            continue
                        total_bytes += len(chunk)
                        chunk_count += 1
                        if settings.debug_mode:
                            print(f"[TTS Stream] chunk={chunk_count}, "
                                  f"bytes={len(chunk)}, total={total_bytes}")
                        yield chunk

                    if status == 2:  # end of stream
                        break

                if settings.debug_mode:
                    print(f"[TTS Stream] Done, {chunk_count} chunks, "
                          f"{total_bytes} total bytes")
                    print()
                return

            except requests.RequestException as e:
                last_error = e
                if attempt < self._max_retries:
                    time.sleep(2 ** attempt)
                    continue

        raise SpeechError(
            f"MiniMax T2A streaming failed after {self._max_retries + 1} attempts"
        ) from last_error

    @staticmethod
    def _decode_audio_hex(audio_hex: str) -> bytes:
        """Decode hex-encoded audio from MiniMax T2A API."""
        return bytes.fromhex(audio_hex.strip())

    def _synthesize_normal(self, text: str, output_path: Path) -> Path:
        """Non-streaming: single request → complete audio."""
        payload = self._build_payload(text, stream=False)

        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                headers = self._build_headers()
                if settings.debug_mode:
                    self._print_request(text, stream=False)
                response = requests.post(
                    self._endpoint,
                    json=payload,
                    headers=headers,
                    timeout=self._timeout,
                )

                if response.status_code == 200:
                    data = response.json()
                    audio_hex = data.get("data", {}).get("audio", "")
                    if not audio_hex:
                        raise SpeechError("MiniMax T2A returned empty audio.")

                    audio_bytes = self._decode_audio_hex(audio_hex)
                    output_path.write_bytes(audio_bytes)
                    if settings.debug_mode:
                        print(f"[TTS Normal] status=200, audio_bytes={len(audio_bytes)}")
                        print()
                    return output_path

                if response.status_code >= 500 and attempt < self._max_retries:
                    time.sleep(2 ** attempt)
                    continue

                raise SpeechError(
                    f"MiniMax T2A request failed (HTTP {response.status_code}): "
                    f"{response.text[:200]}"
                )

            except requests.RequestException as e:
                last_error = e
                if attempt < self._max_retries:
                    time.sleep(2 ** attempt)
                    continue

        raise SpeechError(
            f"MiniMax T2A request failed after {self._max_retries + 1} attempts"
        ) from last_error

    def _build_payload(self, text: str, *, stream: bool) -> dict:
        return {
            "model": self._model,
            "text": text,
            "stream": stream,
            "voice_setting": self._voice_setting,
            "audio_setting": self._audio_setting,
        }

    def _build_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _print_request(self, text: str, *, stream: bool) -> None:
        input_preview = text[:100]
        print(f"[TTS Request]")
        print(f"  URL:      {self._endpoint}")
        print(f"  Model:    {self._model}")
        print(f"  Voice:    {self._voice_setting['voice_id']}")
        print(f"  Format:   {self._audio_setting['format']}")
        print(f"  Stream:   {stream}")
        print(f"  Input:    {input_preview}")
        print()
