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
    speech_api_key: str = ""
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

    # LLM provider: "openai" (OpenAI-compatible API)
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.minimaxi.com/v1"
    llm_model: str = "MiniMax-M3"
    llm_max_tokens: int = 1024
    llm_temperature: float = 0.7

    # Audio
    sample_rate: int = 16000
    channels: int = 1

    # Conversation mode: "llm" (LLM via OpenAI-compatible API) or "tts" (Qwen3-TTS direct)
    conversation_mode: str = "llm"

    # System prompt for LLM conversation mode
    system_prompt: str = (
        "You are Jarvis, a helpful AI voice assistant. "
        "Keep responses concise and conversational. "
        "Limit responses to 2-3 sentences when possible."
    )

    # Interjection tags — MiniMax T2A renders these as non-verbal sounds
    interjection_enabled: bool = False
    interjection_prompt: str = (
        "You may insert interjection tags in your responses to make the speech "
        "more expressive and natural. Available tags:\n"
        "(laughs) laugh, (chuckle) light laugh, (coughs) cough, "
        "(clear-throat) clear throat, (groans) groan, (breath) normal breath, "
        "(pant) panting, (inhale) inhale, (exhale) exhale, "
        "(gasps) gasp, (sniffs) sniff, (sighs) sigh, "
        "(snorts) snort, (burps) burp, (lip-smacking) lip smack, "
        "(humming) humming, (hissing) hiss, (emm) hesitation 'umm', "
        "(sneezes) sneeze.\n"
        "Insert tags naturally where appropriate, e.g. "
        '"今天真是(sighs)太累了" or "(laughs)这个笑话真有趣".'
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

    # Wake words — strict exact/prefix match, no substring/fuzzy matching
    wake_words: list[str] = ["jarvis", "javis", "贾维斯"]

    # Wake responses — randomly chosen when wake word detected (no consecutive repeats)
    wake_responses: list[str] = [
        "嗯？",
        "我在。",
        "怎么了？",
        "在呢。",
        "请讲。",
        "我在听。",
        "有什么事吗？",
        "I'm here.",
        "I'm here sir.",
        "Yes sir.",
    ]

    # VAD
    vad_provider: str = "silero"  # "silero" or "webrtc"
    silero_threshold: float = 0.5  # Speech probability threshold
    silero_min_speech_ms: int = 300
    silero_silence_ms: int = 800
    conversation_timeout: float = 30.0

    # Wake response guard delay (ms) — prevents speaker residual from being captured
    wake_response_guard_ms: int = 500

    # Beeps
    wake_beep_enabled: bool = True
    timeout_beep_enabled: bool = True

    # Voice commands
    exit_commands: list[str] = ["退出", "结束", "停止", "拜拜", "再见"]
    interrupt_commands: list[str] = ["停止", "停一下", "打断", "闭嘴"]

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
    if settings.conversation_mode == "llm" and not settings.llm_api_key:
        missing.append("LLM_API_KEY")
    if settings.speech_provider == "minimax" and not settings.speech_api_key:
        missing.append("SPEECH_API_KEY")
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
