from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from src.config.settings import settings


def get_llm() -> BaseChatModel:
    # if settings.llm_provider == "gemini":
    #     return ChatGoogleGenerativeAI(
    #         model=settings.llm_model,
    #         google_api_key=settings.google_api_key,
    #         temperature=0,
    #     )

    # if settings.llm_provider == "openai":
    #     return ChatOpenAI(
    #         model=settings.llm_model,
    #         api_key=settings.openai_api_key,
    #         temperature=0,
    #     )

    if settings.llm_provider == "claude":
        return ChatAnthropic(
            model=settings.anthropic_llm_model,
            api_key=settings.anthropic_api_key,
            # Sonnet 5 / Opus 5 turn on adaptive thinking by
            # default, which makes response.content a list of
            # thinking/text blocks instead of a plain string.
            # Every agent here parses response.content as a
            # plain JSON string, so thinking must stay disabled.
            thinking={"type": "disabled"},
        )

    raise ValueError(
        f"Unsupported LLM provider: {settings.llm_provider}"
    )