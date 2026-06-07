from jarvis.config import settings
from jarvis.llm.openai_provider import OpenAIProvider


def create_llm_provider() -> OpenAIProvider:
    """Create an LLM provider based on current settings."""
    return OpenAIProvider(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        max_retries=settings.max_retries,
    )
