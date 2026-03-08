from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./metaclassifier.db"
    classifier_provider: str = "openai"
    classifier_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    openai_timeout_seconds: float = 20.0
    datahub_server: str = "http://localhost:8080"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
