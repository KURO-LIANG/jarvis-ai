from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Centralized configuration for Jarvis voice assistant."""

    # OMLX (local ASR/TTS server)
    omlx_base_url: str = "http://127.0.0.1:8000"
    omlx_api_key: str = ""
    omlx_timeout: int = 60

    # ASR model name
    asr_model: str = "Qwen3-ASR-1.7B-8bit"

    # TTS
    tts_model: str = "Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit"
    tts_voice: str = "Vivian"

    # Speech provider: "qwen" (OMLX local TTS) or "minimax" (MiniMax T2A v2 API)
    speech_provider: str = "qwen"
    minimax_speech_url: str = "https://api.minimaxi.com/v1/t2a_v2"
    minimax_speech_model: str = "speech-2.8-turbo"
    minimax_speech_mode: str = "stream"  # "stream" or "normal"

    # MiniMax T2A voice settings
    minimax_speech_voice_id: str = "male-qn-qingse"
    minimax_speech_speed: float = 1.0
    minimax_speech_vol: float = 1.0
    minimax_speech_pitch: int = 0
    minimax_speech_emotion: str = "happy"

    # MiniMax T2A audio output settings
    minimax_speech_audio_format: str = "mp3"
    minimax_speech_sample_rate: int = 32000
    minimax_speech_bitrate: int = 128000
    minimax_speech_channel: int = 1

    # MiniMax (OpenAI-compatible LLM)
    minimax_api_key: str = ""
    minimax_base_url: str = "https://api.minimaxi.com/v1"
    minimax_model: str = "MiniMax-M3"
    minimax_max_tokens: int = 1024
    minimax_temperature: float = 0.7

    # Audio
    sample_rate: int = 16000
    channels: int = 1

    # Conversation mode: "llm" (MiniMax) or "tts" (Qwen3-TTS direct)
    conversation_mode: str = "llm"

    # System prompt for LLM conversation mode
    system_prompt: str = (
        "You are Jarvis, a helpful AI voice assistant. "
        "Keep responses concise and conversational. "
        "Limit responses to 2-3 sentences when possible."
    )

    # Debug mode - skip microphone/ASR, use terminal text input
    debug_mode: bool = False

    # Output paths
    input_wav_path: Path = Path("input.wav")
    output_wav_path: Path = Path("reply.wav")

    # Memory
    memory_enabled: bool = True
    memory_max_turns: int = 10
    memory_auto_extract: bool = True
    memory_storage_path: str = "~/.jarvis/memory"

    # Retry
    max_retries: int = 1

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()


def validate_config() -> list[tuple[str, str]]:
    """Validate required configuration.

    Returns a list of (field_name, error_message) tuples.
    Empty list means config is valid.
    """
    errors: list[tuple[str, str]] = []

    missing = []
    needs_minimax = (
        settings.conversation_mode == "llm"
        or settings.speech_provider == "minimax"
    )
    if needs_minimax and not settings.minimax_api_key:
        missing.append("MINIMAX_API_KEY")
    if not settings.omlx_api_key:
        missing.append("OMLX_API_KEY")

    if missing:
        errors.append((
            ", ".join(missing),
            "Required API key(s) not set.\n"
            "  Copy .env.example to .env and set your API keys:\n"
            "    cp .env.example .env\n"
            "  Or export them as environment variables.",
        ))

    return errors
