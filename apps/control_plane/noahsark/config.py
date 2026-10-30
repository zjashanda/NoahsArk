from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "dev"
    api_prefix: str = "/api/v1"
    database_url: str | None = None
    log_level: str = "INFO"

    # Identity: "dev_headers" (compatibility default), "session" (bearer-like
    # session token required) or "oidc" (stub, fails closed until implemented).
    auth_mode: str = "dev_headers"
    session_ttl_seconds: int = 3600
    dev_session_enabled: bool = True
    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
