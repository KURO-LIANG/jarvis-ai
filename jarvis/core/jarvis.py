import time
from pathlib import Path

from jarvis.asr.qwen_asr import ASRError, QwenASR
from jarvis.audio.player import AudioPlayer, PlaybackError
from jarvis.audio.recorder import MicrophoneRecorder, RecordingError
from jarvis.config import settings
from jarvis.conversation.base import ConversationProvider
from jarvis.conversation.minimax_provider import MiniMaxConversationProvider
from jarvis.conversation.qwen_tts_provider import QwenTTSConversationProvider
from jarvis.core.input_strategy import (
    InputStrategy,
    TextInputStrategy,
    VoiceInputStrategy,
)
from jarvis.llm.base import LLMError
from jarvis.llm.minimax import MiniMaxProvider
from jarvis.memory.manager import MemoryManager
from jarvis.speech.base import SpeechError, SpeechProvider
from jarvis.speech.factory import create_speech_provider
from jarvis.tts.qwen_tts import TTSError


class Jarvis:
    """Orchestrates the voice assistant pipeline:

    Input -> Conversation -> Speech -> Play
    """

    def __init__(self) -> None:
        self._build_input_strategy()
        speech_provider = self._build_speech_provider()
        memory = self._build_memory()
        self._build_conversation_provider(speech_provider, memory)
        self._player = AudioPlayer()

    def _build_input_strategy(self) -> None:
        if settings.debug_mode:
            self._input_strategy: InputStrategy = TextInputStrategy()
        else:
            recorder = MicrophoneRecorder(
                sample_rate=settings.sample_rate,
                channels=settings.channels,
            )
            asr = QwenASR(
                base_url=settings.omlx_base_url,
                api_key=settings.omlx_api_key,
                model=settings.asr_model,
                timeout=settings.omlx_timeout,
                max_retries=settings.max_retries,
            )
            self._input_strategy = VoiceInputStrategy(recorder, asr)

    def _build_speech_provider(self) -> SpeechProvider:
        return create_speech_provider()

    def _build_memory(self) -> MemoryManager | None:
        if not settings.memory_enabled:
            return None
        llm = MiniMaxProvider(
            api_key=settings.minimax_api_key,
            base_url=settings.minimax_base_url,
            model=settings.minimax_model,
            max_retries=settings.max_retries,
        )
        mm = MemoryManager(
            max_turns=settings.memory_max_turns,
            storage_path=Path(settings.memory_storage_path).expanduser()
            / "user_memory.json",
            llm=llm,
            auto_extract=settings.memory_auto_extract,
        )
        mm.load()
        return mm

    def _build_conversation_provider(
        self, speech_provider: SpeechProvider, memory: MemoryManager | None = None
    ) -> None:
        if settings.conversation_mode == "tts":
            self._conversation: ConversationProvider = (
                QwenTTSConversationProvider(speech_provider)
            )
        else:
            self._conversation = MiniMaxConversationProvider(
                speech_provider, memory=memory
            )

    def run(self) -> None:
        """Main interactive loop. Runs until KeyboardInterrupt."""
        while True:
            try:
                self._run_once()
            except KeyboardInterrupt:
                raise
            except RecordingError as e:
                print(f"Recording error: {e}")
            except ASRError as e:
                print(f"ASR error: {e}")
            except LLMError as e:
                print(f"LLM error: {e}")
            except TTSError as e:
                print(f"TTS error: {e}")
            except SpeechError as e:
                print(f"Speech error: {e}")
            except PlaybackError as e:
                print(f"Playback error: {e}")
            except Exception as e:
                print(f"Unexpected error: {e}")

            print()

    def _run_once(self) -> None:
        """Execute one full pipeline cycle."""
        user_text = self._input_strategy.get_input()
        print(f"You: {user_text}")

        t0 = time.time()
        result = self._conversation.respond(user_text)
        t1 = time.time()

        self._player.play(result.audio_path)
        t2 = time.time()

        print(f"[Timing] Conversation: {t1 - t0:.1f}s, "
              f"Playback: {t2 - t1:.1f}s, "
              f"Total: {t2 - t0:.1f}s")
