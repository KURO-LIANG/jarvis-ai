import time
from pathlib import Path

from jarvis.asr.qwen_asr import ASRError, QwenASR
from jarvis.audio.beep import BeepGenerator
from jarvis.audio.continuous_mic import ContinuousMicStream
from jarvis.audio.player import AudioPlayer, PlaybackError
from jarvis.audio.vad_processor import SpeechSegment, VadProcessor
from jarvis.config import settings
from jarvis.conversation.base import ConversationProvider
from jarvis.conversation.minimax_provider import MiniMaxConversationProvider
from jarvis.conversation.qwen_tts_provider import QwenTTSConversationProvider
from jarvis.core.command_detector import CommandDetector
from jarvis.core.input_strategy import TextInputStrategy
from jarvis.core.state_machine import AssistantState, StateMachine
from jarvis.core.wake_word import WakeWordDetector
from jarvis.llm.base import LLMError
from jarvis.llm.minimax import MiniMaxProvider
from jarvis.memory.manager import MemoryManager
from jarvis.speech.base import SpeechError, SpeechProvider
from jarvis.speech.factory import create_speech_provider
from jarvis.tts.qwen_tts import TTSError


class Jarvis:
    """Orchestrates the voice assistant pipeline.

    Voice mode:  continuous mic -> VAD -> ASR -> wake word / commands /
    barge-in -> LLM -> TTS -> threaded playback.

    States: IDLE -> LISTENING -> THINKING -> SPEAKING -> LISTENING
    """

    def __init__(self) -> None:
        self._state = StateMachine()
        self._wake = WakeWordDetector(settings.wake_word)
        self._commands = CommandDetector(settings.exit_commands)

        if not settings.debug_mode:
            self._asr = QwenASR(
                base_url=settings.omlx_base_url,
                api_key=settings.omlx_api_key,
                model=settings.asr_model,
                timeout=settings.omlx_timeout,
                max_retries=settings.max_retries,
            )
        else:
            self._asr = None

        speech_provider = self._build_speech_provider()
        memory = self._build_memory()
        self._build_conversation_provider(speech_provider, memory)
        self._player = AudioPlayer()

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
            self._conversation: ConversationProvider = QwenTTSConversationProvider(
                speech_provider
            )
        else:
            self._conversation = MiniMaxConversationProvider(
                speech_provider, memory=memory
            )

    # -- Entry point --

    def run(self) -> None:
        if settings.debug_mode:
            self._run_debug_loop()
        else:
            self._run_voice_loop()

    # -- Debug loop --

    def _run_debug_loop(self) -> None:
        """Text-based interactive loop."""
        input_strategy = TextInputStrategy()
        while True:
            try:
                user_text = input_strategy.get_input()

                if self._commands.is_exit_command(user_text):
                    print("Jarvis: 好的，已退出聊天模式")
                    break

                print(f"You: {user_text}")

                t0 = time.time()
                result = self._conversation.respond(user_text)
                t1 = time.time()

                self._player.play(result.audio_path)
                self._player.wait()
                t2 = time.time()

                print(
                    f"[Timing] Conversation: {t1 - t0:.1f}s, "
                    f"Playback: {t2 - t1:.1f}s, "
                    f"Total: {t2 - t0:.1f}s"
                )
            except KeyboardInterrupt:
                raise
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

    # -- Voice loop --

    def _run_voice_loop(self) -> None:
        """State-machine-driven continuous listening loop."""
        mic = ContinuousMicStream(
            sample_rate=settings.sample_rate,
            channels=settings.channels,
            blocksize=480,
        )
        vad = VadProcessor(
            sample_rate=settings.sample_rate,
            vad_aggressiveness=settings.vad_aggressiveness,
            frame_ms=30,
            silence_threshold_ms=800,
            min_speech_ms=300,
        )

        self._state.on_state_change(self._make_state_listener(mic))

        mic.start()
        last_speech_time = time.time()

        print()
        print(f'Waiting for wake word: "{settings.wake_word}"...')

        try:
            while True:
                # --- Check for natural playback completion ---
                if self._state.is_speaking() and self._player.playback_done.is_set():
                    self._state.done_speaking()  # SPEAKING -> LISTENING

                # --- Timeout check for LISTENING ---
                if self._state.is_listening():
                    elapsed = time.time() - last_speech_time
                    if elapsed >= settings.conversation_timeout:
                        segment = vad.flush()
                        if segment is not None:
                            self._process_segment(segment)
                        self._state.timeout()  # LISTENING -> IDLE

                # --- Get next audio chunk ---
                chunk = mic.get_chunk(timeout=0.1)

                if chunk is None:
                    continue

                segment = vad.process_frame(chunk)
                if segment is not None:
                    last_speech_time = time.time()
                    self._process_segment(segment)

        except KeyboardInterrupt:
            raise
        finally:
            mic.stop()

    # -- Speech segment routing --

    def _process_segment(self, segment: SpeechSegment) -> None:
        """Transcribe and route based on current state."""
        text = self._transcribe(segment)
        if not text:
            return

        if self._state.is_idle():
            self._handle_idle(text)

        elif self._state.is_listening():
            self._handle_listening(text)

        elif self._state.is_speaking():
            # Barge-in: any speech during playback interrupts
            print(f"[Jarvis] Barge-in detected, stopping playback...")
            self._player.stop()
            self._state.barge_in()  # SPEAKING -> LISTENING
            # Now process the interrupting speech as a new command
            self._handle_listening(text)

        # THINKING: speech is ignored

    # -- State-specific handlers --

    def _handle_idle(self, text: str) -> None:
        """Check for wake word in IDLE state."""
        if not self._wake.is_wake_word(text):
            print(f"[Jarvis] Ignored (no wake word): {text}")
            return

        command = self._wake.strip_wake_word(text)
        self._state.wake_word_detected()  # IDLE -> LISTENING

        if command:
            # User said "jarvis <command>" in one utterance
            self._handle_user_command(command)

    def _handle_listening(self, text: str) -> None:
        """Handle user speech in LISTENING state."""
        if self._commands.is_exit_command(text):
            self._state.exit_conversation()  # LISTENING -> IDLE
            self._play_exit_message()
            return

        print(f"You: {text}")
        self._handle_user_command(text)

    def _handle_user_command(self, text: str) -> None:
        """Process a user command: LLM -> TTS -> play (non-blocking)."""
        self._state.start_thinking()  # LISTENING -> THINKING

        try:
            t0 = time.time()
            result = self._conversation.respond(text)
            t1 = time.time()

            print(f"Jarvis: {result.text}")
            print(f"[Timing] Conversation: {t1 - t0:.1f}s")

            self._state.start_speaking()  # THINKING -> SPEAKING
            self._player.play(result.audio_path)  # non-blocking

        except (LLMError, TTSError, SpeechError) as e:
            print(f"{type(e).__name__}: {e}")
            if self._state.is_thinking():
                self._state.thinking_failed()  # THINKING -> LISTENING

    # -- Helpers --

    def _transcribe(self, segment: SpeechSegment) -> str:
        """Run ASR, return text or empty string. Empty text is silently ignored."""
        assert self._asr is not None, "ASR not available in debug mode"
        try:
            transcription = self._asr.transcribe(segment.audio_path)
            return transcription.text.strip()
        except ASRError as e:
            if "empty text" not in str(e).lower():
                print(f"ASR error: {e}")
            return ""
        finally:
            segment.audio_path.unlink(missing_ok=True)

    def _play_exit_message(self) -> None:
        """Synthesize and play exit notification."""
        try:
            exit_msg = "好的，已退出聊天模式"
            result = self._conversation.respond(exit_msg)
            print(f"Jarvis: {exit_msg}")
            AudioPlayer.play_file(result.audio_path)
            result.audio_path.unlink(missing_ok=True)
        except Exception as e:
            print(f"Exit message failed: {e}")

    def _make_state_listener(self, mic: ContinuousMicStream):
        """Factory for state-change callback."""

        def on_state(new_state: AssistantState) -> None:
            if new_state == AssistantState.LISTENING:
                mic.drain()
                print("\n[Jarvis] Listening...")

            elif new_state == AssistantState.THINKING:
                print("[Jarvis] Thinking...")

            elif new_state == AssistantState.SPEAKING:
                mic.drain()

            elif new_state == AssistantState.IDLE:
                if settings.timeout_beep_enabled:
                    self._play_beep(BeepGenerator.timeout_beep())
                print(
                    f'\n[Jarvis] Timeout — waiting for wake word: '
                    f'"{settings.wake_word}"...'
                )

        return on_state

    @staticmethod
    def _play_beep(beep_path: Path) -> None:
        """Play a beep sound and clean up the temp file."""
        try:
            AudioPlayer.play_file(beep_path)
        finally:
            beep_path.unlink(missing_ok=True)
