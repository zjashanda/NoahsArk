from pydantic import AliasChoices, Field, field_validator
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

    # W3 evidence storage.  The root is server-internal and must never be
    # serialized into an API response; clients only see relative storage keys.
    evidence_storage_root: str = "var/evidence"
    evidence_max_blob_bytes: int = 1024 * 1024 * 1024
    evidence_retention_days: int = 30

    # Test-campaign evidence artifacts (serial logs / tool.log / results.csv /
    # summary_final.json bundled as a zip).  The root is server-internal and is
    # never serialized into an API response; clients only see a relative
    # download URL and the display name.  The cap protects the disk from an
    # unbounded node upload.
    artifact_storage_root: str = "var/artifacts"
    artifact_max_bytes: int = 256 * 1024 * 1024

    # Platform-wide enrollment credential for first-boot node registration.
    # The value is only ever compared, never logged or persisted.
    node_enrollment_token: str = Field(
        default="dev-node-enroll-token",
        validation_alias=AliasChoices(
            "NOAHSARK_NODE_ENROLLMENT_TOKEN", "node_enrollment_token"
        ),
    )

    @field_validator("node_enrollment_token")
    @classmethod
    def _node_enrollment_token_not_blank(cls, value: str) -> str:
        if not value.strip():
            msg = "node_enrollment_token must not be blank"
            raise ValueError(msg)
        return value

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
