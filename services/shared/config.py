from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./metaclassifier.db"
    classifier_provider: str = "openai"
    classifier_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    openai_timeout_seconds: float = 20.0
    classification_service_url: str = "http://classification:8002/classify"
    classification_timeout_seconds: float = 10.0
    datahub_gms_url: str = "http://datahub-gms:8080"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
