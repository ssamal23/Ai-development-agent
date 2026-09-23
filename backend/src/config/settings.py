from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    google_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    llm_provider: str = "gemini"
    llm_model: str = "gemini-2.5-flash"

    repository_path: str

    github_token: str
    github_owner: str
    github_repository: str
    github_base_branch: str = "main"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()