from jarvis.config import settings
from jarvis.conversation.base import ConversationProvider, ConversationResult
from jarvis.llm.base import Message
from jarvis.llm.factory import create_llm_provider
from jarvis.memory.manager import MemoryManager
from jarvis.speech.base import SpeechProvider


class LLMConversationProvider(ConversationProvider):
    """LLM mode: user text → LLM → reply text → SpeechProvider → audio."""

    def __init__(
        self,
        speech_provider: SpeechProvider,
        memory: MemoryManager | None = None,
    ) -> None:
        if settings.debug_mode:
            print("[Conversation Provider] LLMConversationProvider"
                  f" (speech={type(speech_provider).__name__})")
        self._llm = create_llm_provider()
        self._speech = speech_provider
        self._memory = memory

    def respond(self, user_text: str) -> ConversationResult:
        # Build messages with conversation history
        messages: list[Message] = []
        if self._memory:
            messages = self._memory.get_recent_messages()
        messages.append(Message(role="user", content=user_text))

        # Build system prompt with long-term memory context
        system_prompt = settings.system_prompt
        if settings.interjection_enabled:
            system_prompt = system_prompt + "\n\n" + settings.interjection_prompt
        if self._memory:
            mem_ctx = self._memory.build_context()
            if mem_ctx:
                system_prompt = mem_ctx + "\n" + system_prompt

        response = self._llm.chat(
            messages=messages,
            system_prompt=system_prompt,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
        # Save to memory
        if self._memory:
            self._memory.save_turn(user_text, response.content)
            self._memory.extract_and_update(user_text, response.content)

        output_path = settings.output_wav_path.with_suffix(
            f".{self._speech.audio_format}"
        )
        self._speech.synthesize(response.content, output_path)

        return ConversationResult(
            text=response.content,
            audio_path=output_path,
        )
