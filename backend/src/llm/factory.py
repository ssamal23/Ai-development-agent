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
            model=settings.llm_model,
            api_key=settings.anthropic_api_key,
            temperature=0,
        )

    raise ValueError(
        f"Unsupported LLM provider: {settings.llm_provider}"
    )