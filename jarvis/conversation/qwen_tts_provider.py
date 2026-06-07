from jarvis.config import settings
from jarvis.conversation.base import ConversationProvider, ConversationResult
from jarvis.speech.base import SpeechProvider


class QwenTTSConversationProvider(ConversationProvider):
    """TTS bypass mode: user text → SpeechProvider → audio.

    Qwen3-TTS-12Hz-1.7B-CustomVoice handles both reasoning and speech
    generation in a single step. No separate LLM call needed.
    """

    def __init__(self, speech_provider: SpeechProvider) -> None:
        if settings.debug_mode:
            print("[Conversation Provider] QwenTTSConversationProvider"
                  f" (speech={type(speech_provider).__name__})")
        self._speech = speech_provider

    def respond(self, user_text: str) -> ConversationResult:
        output_path = settings.output_wav_path.with_suffix(
            f".{self._speech.audio_format}"
        )
        self._speech.synthesize(user_text, output_path)

        return ConversationResult(
            text=None,
            audio_path=output_path,
        )
