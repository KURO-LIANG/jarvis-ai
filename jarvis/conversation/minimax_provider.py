from jarvis.config import settings
from jarvis.conversation.base import ConversationProvider, ConversationResult
from jarvis.llm.base import Message
from jarvis.llm.minimax import MiniMaxProvider
from jarvis.memory.manager import MemoryManager
from jarvis.speech.base import SpeechProvider


class MiniMaxConversationProvider(ConversationProvider):
    """LLM mode: user text → MiniMax → reply text → SpeechProvider → audio."""

    def __init__(
        self,
        speech_provider: SpeechProvider,
        memory: MemoryManager | None = None,
    ) -> None:
        print("[Conversation Provider] MiniMaxConversationProvider"
              f" (speech={type(speech_provider).__name__})")
        self._llm = MiniMaxProvider(
            api_key=settings.minimax_api_key,
            base_url=settings.minimax_base_url,
            model=settings.minimax_model,
            max_retries=settings.max_retries,
        )
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
        if self._memory:
            mem_ctx = self._memory.build_context()
            if mem_ctx:
                system_prompt = mem_ctx + "\n" + system_prompt

        print("Thinking...")
        response = self._llm.chat(
            messages=messages,
            system_prompt=system_prompt,
            temperature=settings.minimax_temperature,
            max_tokens=settings.minimax_max_tokens,
        )
        print(f"Jarvis: {response.content}")

        # Save to memory
        if self._memory:
            self._memory.save_turn(user_text, response.content)
            self._memory.extract_and_update(user_text, response.content)

        print("Generating speech...")
        output_path = settings.output_wav_path.with_suffix(
            f".{self._speech.audio_format}"
        )
        self._speech.synthesize(response.content, output_path)

        return ConversationResult(
            text=response.content,
            audio_path=output_path,
        )
