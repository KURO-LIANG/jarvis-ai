import re

from openai import OpenAI

from jarvis.config import settings
from jarvis.llm.base import ChatResponse, LLMError, LLMProvider, Message


def _mask_key(api_key: str) -> str:
    """Mask an API key, showing only first 8 and last 4 characters."""
    if len(api_key) <= 12:
        return "*" * len(api_key)
    return f"{api_key[:8]}...{api_key[-4:]}"


class OpenAIProvider(LLMProvider):
    """LLM provider for any OpenAI-compatible API (DeepSeek, MiniMax, OpenAI, Ollama, etc.)."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        max_retries: int = 1,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            max_retries=max_retries,
        )
        self._model = model

    def chat(
        self,
        messages: list[Message],
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> ChatResponse:
        """Send chat completion request."""
        api_messages: list[dict[str, str]] = []

        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            api_messages.append({"role": msg.role, "content": msg.content})

        if settings.debug_mode:
            self._print_request(api_messages, temperature, max_tokens)

        try:
            completion = self._client.chat.completions.create(
                model=self._model,
                messages=api_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            raise LLMError(f"LLM request failed: {e}") from e

        choice = completion.choices[0]
        content = self._strip_thinking(choice.message.content or "")
        response = ChatResponse(
            content=content,
            model=completion.model,
            usage={
                "prompt_tokens": completion.usage.prompt_tokens if completion.usage else 0,
                "completion_tokens": completion.usage.completion_tokens if completion.usage else 0,
            },
        )
        if settings.debug_mode:
            self._print_response(response)
        return response

    def _print_request(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> None:
        print(f"[LLM Request]")
        print(f"  Provider:    {settings.llm_provider}")
        print(f"  Base URL:    {self._base_url}")
        print(f"  API Key:     {_mask_key(self._api_key)}")
        print(f"  Model:       {self._model}")
        print(f"  MaxTokens:   {max_tokens}")
        print(f"  Temperature: {temperature}")
        for i, msg in enumerate(messages):
            content_preview = msg["content"][:100]
            print(f"  Messages[{i}]: role={msg['role']}, content={content_preview}")
        print()

    def _print_response(self, response: ChatResponse) -> None:
        usage_info = ""
        if response.usage:
            usage_info = (
                f"prompt_tokens={response.usage.get('prompt_tokens', '?')}, "
                f"completion_tokens={response.usage.get('completion_tokens', '?')}"
            )
        print(f"[LLM Response] model={response.model}, {usage_info}")
        print()

    @staticmethod
    def _strip_thinking(content: str) -> str:
        """Remove <think>...</think> blocks from the response."""
        return re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
