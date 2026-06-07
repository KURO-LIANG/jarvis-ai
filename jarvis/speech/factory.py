from jarvis.config import settings
from jarvis.speech.base import SpeechProvider
from jarvis.speech.minimax_speech_provider import MiniMaxSpeechProvider
from jarvis.speech.qwen_tts_provider import QwenSpeechProvider


def create_speech_provider() -> SpeechProvider:
    """Create a SpeechProvider based on current configuration."""
    sp = settings.speech_provider

    if sp == "qwen":
        return QwenSpeechProvider(
            base_url=settings.omlx_base_url,
            api_key=settings.omlx_api_key,
            model=settings.tts_model,
            voice=settings.tts_voice,
            timeout=settings.omlx_timeout,
            max_retries=settings.max_retries,
        )

    if sp == "minimax":
        return MiniMaxSpeechProvider(
            api_key=settings.minimax_api_key,
            url=settings.minimax_speech_url,
            model=settings.minimax_speech_model,
            mode=settings.minimax_speech_mode,
            voice_setting={
                "voice_id": settings.minimax_speech_voice_id,
                "speed": settings.minimax_speech_speed,
                "vol": settings.minimax_speech_vol,
                "pitch": settings.minimax_speech_pitch,
                "emotion": settings.minimax_speech_emotion,
            },
            audio_setting={
                "sample_rate": settings.minimax_speech_sample_rate,
                "bitrate": settings.minimax_speech_bitrate,
                "format": settings.minimax_speech_audio_format,
                "channel": settings.minimax_speech_channel,
            },
            timeout=settings.omlx_timeout,
            max_retries=settings.max_retries,
        )

    raise ValueError(f"Unknown speech_provider: {sp!r}")
