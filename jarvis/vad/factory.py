from jarvis.config import settings
from jarvis.vad.base import VadProvider
from jarvis.vad.silero_vad import SileroVadProvider


def create_vad_provider() -> VadProvider:
    """Factory: create VAD provider from settings."""
    provider_type = settings.vad_provider

    if provider_type == "silero":
        return SileroVadProvider(
            sample_rate=settings.sample_rate,
            threshold=settings.silero_threshold,
            min_speech_ms=settings.silero_min_speech_ms,
            silence_ms=settings.silero_silence_ms,
        )

    if provider_type == "webrtc":
        raise ValueError(
            "WebRTC VAD is deprecated in V3. Use vad_provider=silero."
        )

    raise ValueError(f"Unknown VAD provider: {provider_type}")
