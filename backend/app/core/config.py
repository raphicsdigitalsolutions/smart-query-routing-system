"""Centralized application configuration.

All environment-driven values live here so that business logic never reads
``os.environ`` directly. Values are loaded from ``backend/.env`` when present.
"""

import hashlib
import re
from functools import lru_cache
from pathlib import Path

from cryptography.fernet import Fernet
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

# backend/.env (parents[0]=core, [1]=app, [2]=backend)
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

# One-way fingerprints of secrets that ship in examples/tests. Storing hashes
# rather than literal values keeps those values out of source while still
# preventing a copied development key from being used in production.
_KNOWN_DEV_SECRET_HASHES = frozenset(
    {
        "ab059a58e2432460e519114f0634a98f486f7a14c140151281855fc957f197c3",
        "2a0582e6c149233b36e10f23046e8c63280ca2d300d89ad35bc5a680964e2170",
        "79ef599b03c84b902bc2c21405ad47203ca5606291b87fc383219ccc0c9d77f6",
        "720b25fe9e71c398d8631167094c5656a62126c9ed1fef637da0a545094620f6",
        "5dc8fa71b69b29db7d7c934c7a8cf5fe4ccc44334dcd580ef1ef9e48936b05e3",
    }
)
_PLACEHOLDER_PATTERN = re.compile(
    r"change|replace|your|example|placeholder|dummy|sample|test|dev|local|"
    r"not[-_ ]?for[-_ ]?prod|not[-_ ]?secure|secret|password|admin",
    re.IGNORECASE,
)
_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
# The Compose stack uses an internal, non-published Postgres service. External
# managed databases must use TLS; internal container networking is the narrow
# exception that keeps the provided Compose example functional.
_INTERNAL_DB_HOSTS = frozenset({"postgres"})
_SECURE_SSL_MODES = frozenset({"require", "verify-ca", "verify-full"})


def _secret_hash(value: str) -> str:
    return hashlib.sha256(value.strip().encode("utf-8")).hexdigest()


def is_placeholder_secret(value: str | None) -> bool:
    """Return True for empty, example, test, or known development secrets."""
    if value is None:
        return True
    cleaned = value.strip()
    if not cleaned or _secret_hash(cleaned) in _KNOWN_DEV_SECRET_HASHES:
        return True
    return bool(_PLACEHOLDER_PATTERN.search(cleaned))


def _is_valid_fernet_key(value: str | None) -> bool:
    if not value:
        return False
    try:
        Fernet(value.strip().encode("utf-8"))
    except (TypeError, ValueError):
        return False
    return True


def _validate_production_settings(instance: "Settings") -> None:
    """Fail closed on unsafe production configuration without exposing values."""
    environment = instance.ENVIRONMENT.strip().lower()
    if environment != "production":
        return

    if instance.DEBUG:
        raise ValueError("DEBUG cannot be enabled in production")

    if instance.ALLOW_GLOBAL_OPENAI_FALLBACK:
        raise ValueError("ALLOW_GLOBAL_OPENAI_FALLBACK cannot be enabled in production")

    if instance.JWT_ALGORITHM.upper() != "HS256":
        raise ValueError("JWT_ALGORITHM must be HS256 in production")

    jwt_secret = instance.JWT_SECRET_KEY or ""
    if not jwt_secret:
        raise ValueError("JWT_SECRET_KEY is required in production")
    if is_placeholder_secret(jwt_secret):
        raise ValueError("JWT_SECRET_KEY is a placeholder or known development value")
    if len(jwt_secret) < 32 or len(set(jwt_secret)) < 10:
        raise ValueError("JWT_SECRET_KEY must be a long, high-entropy value")

    fernet_key = instance.BYOK_ENCRYPTION_KEY or ""
    if not fernet_key:
        raise ValueError("BYOK_ENCRYPTION_KEY is required in production")
    if is_placeholder_secret(fernet_key):
        raise ValueError("BYOK_ENCRYPTION_KEY is a known development value")
    if not _is_valid_fernet_key(fernet_key):
        raise ValueError("BYOK_ENCRYPTION_KEY must be a valid Fernet key")

    try:
        database_url = make_url(instance.DATABASE_URL)
    except Exception:
        raise ValueError("DATABASE_URL must be a valid SQLAlchemy URL") from None
    if database_url.get_backend_name() != "postgresql":
        raise ValueError("DATABASE_URL must use PostgreSQL in production")
    if not database_url.username or is_placeholder_secret(database_url.username):
        raise ValueError("DATABASE_URL must use a non-placeholder username")
    database_password = database_url.password or ""
    if is_placeholder_secret(database_password):
        raise ValueError("DATABASE_URL must use a non-placeholder password")
    if len(database_password) < 12:
        raise ValueError("DATABASE_URL password must be at least 12 characters")
    if not database_url.host or database_url.host.lower() in _LOCAL_HOSTS:
        raise ValueError("DATABASE_URL must not use a localhost host in production")
    ssl_mode = str(dict(database_url.query or {}).get("sslmode", "")).lower()
    if (
        (database_url.host or "").lower() not in _INTERNAL_DB_HOSTS
        and ssl_mode not in _SECURE_SSL_MODES
    ):
        raise ValueError("External DATABASE_URL must require TLS with sslmode=require|verify-ca|verify-full")

    origins = [str(origin).strip().lower() for origin in instance.BACKEND_CORS_ORIGINS]
    if any(
        origin == "*" or is_placeholder_secret(origin)
        for origin in origins
    ):
        raise ValueError("BACKEND_CORS_ORIGINS must not contain wildcard, localhost, or placeholder origins")

    if instance.EMAIL_NOTIFICATIONS_ENABLED and is_placeholder_secret(instance.MAIL_FROM):
        raise ValueError("MAIL_FROM must be a real sender domain when email notifications are enabled")

    if instance.GOOGLE_OAUTH_ENABLED and is_placeholder_secret(instance.GOOGLE_OAUTH_CLIENT_ID):
        raise ValueError("GOOGLE_OAUTH_CLIENT_ID is required when Google OAuth is enabled")

    if instance.WHATSAPP_ENABLED and (
        is_placeholder_secret(instance.WHATSAPP_ACCESS_TOKEN)
        or is_placeholder_secret(instance.WHATSAPP_PHONE_NUMBER_ID)
        or is_placeholder_secret(instance.WHATSAPP_VERIFY_TOKEN)
    ):
        raise ValueError("WhatsApp credentials are required when WhatsApp is enabled")

    if instance.INTAKE_WEBHOOK_TOKEN and is_placeholder_secret(instance.INTAKE_WEBHOOK_TOKEN):
        raise ValueError("INTAKE_WEBHOOK_TOKEN must not be a placeholder value")


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    PROJECT_NAME: str = "Smart Query Routing System"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    # development | staging | production - gates unsafe dev-only tooling.
    ENVIRONMENT: str = "development"

    # Local Vite dev server origins. Override with BACKEND_CORS_ORIGINS in .env.
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Database (Phase 3). Default matches the local Docker Compose placeholder.
    DATABASE_URL: str = (
        "postgresql+psycopg://smartquery:change-me-local-dev@localhost:5432/smartquery_db"
    )
    TEST_DATABASE_URL: str = ""
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_ECHO: bool = False

    # Authentication (Phase 4). JWT_SECRET_KEY is intentionally REQUIRED in
    # production; development uses an ephemeral per-process secret if unset.
    JWT_SECRET_KEY: str | None = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    MIN_PASSWORD_LENGTH: int = 12

    # AI provider (Phase 6). Secrets stay server-side and are never logged.
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_TIMEOUT_SECONDS: float = Field(default=20.0, gt=0, le=120)
    AI_MAX_INPUT_TOKENS: int = Field(default=3000, ge=256, le=16000)
    AI_MAX_OUTPUT_TOKENS: int = Field(default=800, ge=64, le=4000)
    AI_LLM_ATTEMPTS: int = Field(default=2, ge=1, le=4)
    AI_GRAPH_TIMEOUT_SECONDS: float = Field(default=60.0, gt=0, le=180)
    AI_GRAPH_RECURSION_LIMIT: int = Field(default=12, ge=4, le=32)
    AI_MIN_CONFIDENCE: float = Field(default=0.35, ge=0, le=1)
    # Optional JSON file of approved knowledge documents. Empty means abstain.
    AI_KNOWLEDGE_FILE: str = ""

    # Email delivery (Phase 7). No secret is ever logged or returned by the API.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    MAIL_FROM: str = "noreply@example.com"
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    SMTP_TIMEOUT_SECONDS: float = Field(default=10.0, gt=0, le=60)
    SMTP_ATTEMPTS: int = Field(default=3, ge=1, le=5)
    EMAIL_NOTIFICATIONS_ENABLED: bool = True

    # Outbound WhatsApp (Meta Cloud API). Tokens stay server-side.
    WHATSAPP_ENABLED: bool = False
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_VERIFY_TOKEN: str = ""
    WHATSAPP_API_VERSION: str = "v21.0"

    # Inbound integrations (email/webhook adapters).
    INTAKE_WEBHOOK_TOKEN: str = ""
    GOOGLE_OAUTH_CLIENT_ID: str = ""
    GOOGLE_OAUTH_ENABLED: bool = False

    # BYOK secret storage and provider fallback policy.
    BYOK_ENCRYPTION_KEY: str = ""
    ALLOW_GLOBAL_OPENAI_FALLBACK: bool = False

    # Deterministic SLA / escalation worker.
    SLA_HOURS: int = Field(default=24, ge=1, le=720)
    ESCALATION_SWEEP_MINUTES: int = Field(default=60, ge=1, le=1440)

    # Uploads and abuse controls.
    MAX_UPLOAD_BYTES: int = Field(default=5 * 1024 * 1024, ge=1024, le=50 * 1024 * 1024)
    ALLOWED_UPLOAD_TYPES: str = "pdf,txt,md"
    # Ticket attachment bytes live outside the web root and the database.
    # Empty resolves to <backend cwd>/var/attachments for local development.
    ATTACHMENT_STORAGE_DIR: str = ""
    AI_RATE_LIMIT_PER_MINUTE: int = Field(default=20, ge=1, le=300)

    @model_validator(mode="after")
    def _enforce_production_secret_policy(self) -> "Settings":
        _validate_production_settings(self)
        return self

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance (overridable in tests)."""
    return Settings()


settings = get_settings()
