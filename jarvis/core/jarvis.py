import random
import time
from pathlib import Path

from jarvis.asr.qwen_asr import ASRError, QwenASR
from jarvis.audio.beep import BeepGenerator
from jarvis.audio.continuous_mic import ContinuousMicStream
from jarvis.audio.player import AudioPlayer, PlaybackError
from jarvis.config import settings
from jarvis.conversation.base import ConversationProvider
from jarvis.conversation.llm_provider import LLMConversationProvider
from jarvis.conversation.qwen_tts_provider import QwenTTSConversationProvider
from jarvis.core.command_detector import CommandDetector
from jarvis.core.input_strategy import TextInputStrategy
from jarvis.core.state_machine import AssistantState, StateMachine
from jarvis.llm.base import LLMError
from jarvis.llm.factory import create_llm_provider
from jarvis.memory.manager import MemoryManager
from jarvis.speech.base import SpeechError, SpeechProvider
from jarvis.speech.factory import create_speech_provider
from jarvis.tts.qwen_tts import TTSError
from jarvis.core.wake_word import WakeWordDetector
from jarvis.vad.base import SpeechSegment
from jarvis.vad.factory import create_vad_provider


class Jarvis:
    """Orchestrates the voice assistant pipeline.

    Architecture:
      IDLE:          Mic -> Silero VAD -> ASR -> strict wake word match
      WAKE_RESPONSE: Play wake reply, VAD/ASR disabled
      LISTENING:     Mic -> Silero VAD -> ASR -> LLM -> TTS -> loop
      SPEAKING:      Mic -> Silero VAD -> ASR -> wake-word-only barge-in

    States: IDLE -> WAKE_RESPONSE -> LISTENING -> THINKING -> SPEAKING -> LISTENING
    """

    def __init__(self) -> None:
        self._state = StateMachine()
        self._commands = CommandDetector(
            settings.exit_commands, settings.interrupt_commands
        )

        if not settings.debug_mode:
            self._wake_word_detector = WakeWordDetector(settings.wake_words)
            self._vad_provider = create_vad_provider()
            self._asr = QwenASR(
                base_url=settings.omlx_base_url,
                api_key=settings.omlx_api_key,
                model=settings.asr_model,
                timeout=settings.omlx_timeout,
                max_retries=settings.max_retries,
            )
        else:
            self._wake_word_detector = None
            self._vad_provider = None
            self._asr = None

        speech_provider = self._build_speech_provider()
        self._speech = speech_provider  # retained for fixed-reply TTS (no LLM)
        memory = self._build_memory()
        self._build_conversation_provider(speech_provider, memory)
        self._waiting_since: float | None = None
        self._last_wake_response: str | None = None
        self._request_start_time: float = 0.0
        self._player = AudioPlayer()

    def _build_speech_provider(self) -> SpeechProvider:
        return create_speech_provider()

    def _build_memory(self) -> MemoryManager | None:
        if not settings.memory_enabled:
            return None
        llm = create_llm_provider()
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
            self._conversation = LLMConversationProvider(
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

                start = time.time()
                result = self._conversation.respond(user_text)
                elapsed = time.time() - start

                print(f"Jarvis: {result.text}")
                print(f"[ AI ] Latency: {elapsed:.1f}s")
                self._player.play(result.audio_path)
                self._player.wait()
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
        """State-machine-driven continuous listening loop.

        IDLE:          Silero VAD → ASR → text wake word match.
        WAKE_RESPONSE: Wait for wake reply playback + guard delay.
        LISTENING:     Silero VAD → ASR → command routing.
        SPEAKING:      Silero VAD → ASR → wake-word barge-in.
        THINKING:      Mic chunks are skipped.
        """
        mic = ContinuousMicStream(
            sample_rate=settings.sample_rate,
            channels=settings.channels,
            blocksize=512,  # 32ms — minimum Silero VAD accepts (sr/len <= 31.25)
        )

        self._state.on_state_change(self._make_state_listener(mic))
        self._mic = mic

        mic.start()

        words = ", ".join(f'"{w}"' for w in settings.wake_words)
        print()
        print(f"Waiting for wake words: {words}...")

        try:
            while True:
                # --- Check for natural playback completion ---
                if self._state.is_speaking() and self._player.playback_done.is_set():
                    self._state.done_speaking()  # SPEAKING -> LISTENING

                # --- Timeout check for LISTENING ---
                if self._state.is_listening() and self._waiting_since is not None:
                    elapsed = time.time() - self._waiting_since
                    if elapsed >= settings.conversation_timeout:
                        print("[ AI ] Conversation timeout.")
                        segment = self._vad_provider.flush()
                        if segment is not None:
                            self._process_conversation_segment(segment)
                        self._state.timeout()  # LISTENING -> IDLE

                # --- Get next audio chunk ---
                chunk = mic.get_chunk(timeout=0.1)
                if chunk is None:
                    continue

                # --- Route by state ---
                if self._state.is_idle():
                    # IDLE: VAD → ASR → wake word text match
                    segment = self._vad_provider.process_frame(chunk)
                    if segment is not None:
                        print("[ AI ] Heard speech, checking...")
                        text = self._transcribe(segment)
                        if text and self._wake_word_detector.is_wake_word(text):
                            self._vad_provider.reset()
                            stripped = self._wake_word_detector.strip_wake_word(text)
                            self._state.wake_word_detected()  # IDLE -> WAKE_RESPONSE
                            if stripped:
                                # Wake word + command: skip wake response, go to LISTENING
                                self._request_start_time = time.time()
                                self._state.wake_response_done()  # WAKE_RESPONSE -> LISTENING
                                self._process_conversation_command(stripped)
                            else:
                                # Only wake word: play random wake response
                                self._reply_wake()
                        else:
                            if text:
                                print(f'[ AI ] Ignored: "{text}"')
                            self._vad_provider.reset()
                            self._mic.drain()

                elif self._state.is_wake_response():
                    # WAKE_RESPONSE: no VAD/ASR, wait for wake reply to finish
                    if self._player.playback_done.is_set():
                        time.sleep(settings.wake_response_guard_ms / 1000)
                        self._state.wake_response_done()  # WAKE_RESPONSE -> LISTENING

                elif self._state.is_listening():
                    segment = self._vad_provider.process_frame(chunk)
                    if segment is not None:
                        self._process_conversation_segment(segment)

                elif self._state.is_speaking():
                    # Barge-in: only specific interrupt commands trigger
                    segment = self._vad_provider.process_frame(chunk)
                    if segment is not None:
                        self._process_barge_in_segment(segment)

                # THINKING: skip mic processing

        except KeyboardInterrupt:
            raise
        finally:
            mic.stop()
            self._mic = None

    # -- Segment handlers --

    def _process_conversation_segment(self, segment: SpeechSegment) -> None:
        """Transcribe and handle speech in LISTENING state."""
        self._request_start_time = time.time()
        text = self._transcribe(segment)
        if not text:
            return
        self._process_conversation_command(text)

    def _process_conversation_command(self, text: str) -> None:
        """Process a user command in LISTENING state."""
        if self._commands.is_exit_command(text):
            self._state.exit_conversation()  # LISTENING -> IDLE
            self._vad_provider.reset()
            self._reply_audio("好的，再见。")
            self._mic.drain()
            return

        print(f"You: {text}")
        self._handle_user_command(text)

    def _process_barge_in_segment(self, segment: SpeechSegment) -> None:
        """Only wake word can interrupt TTS playback."""
        text = self._transcribe(segment)
        if not text:
            return

        if self._wake_word_detector.is_wake_word(text):
            stripped = self._wake_word_detector.strip_wake_word(text)
            print("[ AI ] Wake word detected, stopping playback...")
            self._player.stop()
            time.sleep(0.3)
            self._state.barge_in()  # SPEAKING -> LISTENING
            if stripped:
                self._request_start_time = time.time()
                self._process_conversation_command(stripped)
            else:
                self._reply_wake()

    def _handle_user_command(self, text: str) -> None:
        """Process a user command: LLM -> TTS -> play (non-blocking)."""
        self._state.start_thinking()  # LISTENING -> THINKING

        try:
            result = self._conversation.respond(text)

            elapsed = time.time() - self._request_start_time
            print(f"Jarvis: {result.text}")
            print(f"[ AI ] Latency: {elapsed:.1f}s")

            self._state.start_speaking()  # THINKING -> SPEAKING
            self._player.play(result.audio_path)  # non-blocking

        except (LLMError, TTSError, SpeechError) as e:
            print(f"{type(e).__name__}: {e}")
            if self._state.is_thinking():
                self._state.thinking_failed()  # THINKING -> IDLE

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

    def _reply_audio(self, text: str) -> None:
        """Synthesize text via speech provider and play non-blocking (no LLM)."""
        try:
            import tempfile

            ext = self._speech.audio_format
            with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as f:
                output_path = Path(f.name)
            audio_path = self._speech.synthesize(text, output_path)
            print(f"Jarvis: {text}")
            self._player.play(audio_path)
        except Exception as e:
            print(f"Reply audio failed: {e}")

    def _reply_wake(self) -> None:
        """Play a random wake response, avoiding consecutive repeats."""
        candidates = [r for r in settings.wake_responses if r != self._last_wake_response]
        if not candidates:
            candidates = settings.wake_responses
        response = random.choice(candidates)
        self._last_wake_response = response
        self._reply_audio(response)

    def _make_state_listener(self, mic: ContinuousMicStream):
        """Factory for state-change callback."""

        def on_state(new_state: AssistantState) -> None:
            if new_state == AssistantState.WAKE_RESPONSE:
                mic.drain()

            elif new_state == AssistantState.LISTENING:
                self._waiting_since = time.time()
                mic.drain()
                print("\n[ AI ] Listening...")

            elif new_state == AssistantState.THINKING:
                self._waiting_since = None
                print("[ AI ] Thinking...")

            elif new_state == AssistantState.SPEAKING:
                mic.drain()

            elif new_state == AssistantState.IDLE:
                if settings.timeout_beep_enabled:
                    self._play_beep(BeepGenerator.timeout_beep())
                mic.drain()
                words = ", ".join(f'"{w}"' for w in settings.wake_words)
                print(
                    f"\n[ AI ] Timeout — waiting for wake words: {words}..."
                )

        return on_state

    @staticmethod
    def _play_beep(beep_path: Path) -> None:
        """Play a beep sound and clean up the temp file."""
        try:
            AudioPlayer.play_file(beep_path)
        finally:
            beep_path.unlink(missing_ok=True)
