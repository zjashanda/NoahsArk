from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "dev"
    api_prefix: str = "/api/v1"
    database_url: str | None = None
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
