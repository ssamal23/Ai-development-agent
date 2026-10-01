from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # google_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    llm_provider: str = "claude"
    # llm_model: str = "gemini-2.5-flash"
    anthropic_llm_model: str = "claude-sonnet-5"

    repository_path: str

    github_token: str
    github_owner: str
    github_repository: str
    github_base_branch: str = "main"

    figma_api_token: str = ""

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()