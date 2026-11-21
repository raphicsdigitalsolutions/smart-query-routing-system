"""Regression tests for release hardening and production config validation."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from app.core.config import Settings, is_placeholder_secret
from app.core.errors import safe_exception_summary

_SAFE_JWT = "Q7wE9rT4yU8iO3pA6sD0fG5hJ2kL9zX1cV4bN7mQ0wE3rT6yU8iO2pA"
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _safe_fernet_key() -> str:
    for _ in range(20):
        key = Fernet.generate_key().decode("ascii")
        if not is_placeholder_secret(key):
            return key
    raise RuntimeError("could not generate a non-placeholder test key")


def _production_env(**overrides: object) -> dict[str, object]:
    env: dict[str, object] = {
        "ENVIRONMENT": "production",
        "DEBUG": False,
        "JWT_SECRET_KEY": _SAFE_JWT,
        "BYOK_ENCRYPTION_KEY": _safe_fernet_key(),
        "ALLOW_GLOBAL_OPENAI_FALLBACK": False,
        "JWT_ALGORITHM": "HS256",
        "DATABASE_URL": (
            "postgresql+psycopg://squser:Lq9Xm2Rt7Yb4Vn8Zc1Kp5@db.internal:5432/"
            "smartquery?sslmode=require"
        ),
        "BACKEND_CORS_ORIGINS": ["https://smartquery.university.edu"],
        "MAIL_FROM": "noreply@university.edu",
        "EMAIL_NOTIFICATIONS_ENABLED": True,
        "GOOGLE_OAUTH_ENABLED": False,
        "WHATSAPP_ENABLED": False,
        "INTAKE_WEBHOOK_TOKEN": "",
    }
    env.update(overrides)
    return env


def _make_settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **_production_env(**overrides))


def _known_dev_fernet_key() -> str:
    text = Path(__file__).with_name("conftest.py").read_text(encoding="utf-8")
    match = re.search(r'"BYOK_ENCRYPTION_KEY"\s*,\s*"([^"]+)"', text)
    assert match is not None
    return match.group(1)


def test_production_accepts_strict_safe_configuration() -> None:
    settings = _make_settings()
    assert settings.ENVIRONMENT.lower() == "production"
    assert settings.JWT_SECRET_KEY == _SAFE_JWT
    assert is_placeholder_secret(settings.BYOK_ENCRYPTION_KEY) is False


def test_local_development_configuration_remains_usable() -> None:
    settings = Settings(_env_file=None, ENVIRONMENT="development")
    assert settings.ENVIRONMENT == "development"
    assert settings.DEBUG is False


def test_production_accepts_internal_compose_database_without_tls() -> None:
    settings = _make_settings(
        DATABASE_URL=(
            "postgresql+psycopg://smartquery:Lq9Xm2Rt7Yb4Vn8Zc1Kp5@postgres:5432/smartquery_db"
        )
    )
    assert settings.DATABASE_URL.startswith("postgresql+psycopg://")


def test_exception_summary_does_not_retain_provider_text_or_secrets() -> None:
    exc = RuntimeError("request failed with bearer FAKE-SECRET-MARKER-DO-NOT-LOG")
    summary = safe_exception_summary(exc, "SMTP delivery")
    assert "FAKE-SECRET-MARKER-DO-NOT-LOG" not in summary
    assert "request failed" not in summary
    assert summary == "SMTP delivery failed (RuntimeError)"


@pytest.mark.parametrize(
    "overrides",
    [
        {"DEBUG": True},
        {"ALLOW_GLOBAL_OPENAI_FALLBACK": True},
        {"JWT_ALGORITHM": "none"},
        {"JWT_SECRET_KEY": ""},
        {"JWT_SECRET_KEY": "change-me-local-dev"},
        {"JWT_SECRET_KEY": "short"},
        {"BYOK_ENCRYPTION_KEY": ""},
        {"BYOK_ENCRYPTION_KEY": "not-a-fernet-key"},
        {"DATABASE_URL": "postgresql+psycopg://squser:change-me-local-dev@db.internal:5432/smartquery?sslmode=require"},
        {"DATABASE_URL": "postgresql+psycopg://squser:Lq9Xm2Rt7Yb4Vn8Zc1Kp5@localhost:5432/smartquery?sslmode=require"},
        {"DATABASE_URL": "postgresql+psycopg://squser:Lq9Xm2Rt7Yb4Vn8Zc1Kp5@db.internal:5432/smartquery"},
        {"DATABASE_URL": "sqlite:///local.db"},
        {"BACKEND_CORS_ORIGINS": ["*"]},
        {"BACKEND_CORS_ORIGINS": ["http://localhost:3000"]},
        {"BACKEND_CORS_ORIGINS": ["https://smartquery.example.edu"]},
        {"MAIL_FROM": "noreply@example.com"},
        {"GOOGLE_OAUTH_ENABLED": True, "GOOGLE_OAUTH_CLIENT_ID": "REPLACE_WITH_CLIENT_ID"},
        {"WHATSAPP_ENABLED": True, "WHATSAPP_ACCESS_TOKEN": "REPLACE_WITH_TOKEN"},
        {"INTAKE_WEBHOOK_TOKEN": "REPLACE_WITH_TOKEN"},
    ],
)
def test_production_rejects_unsafe_configuration(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        _make_settings(**overrides)


def test_production_rejects_known_development_fernet_key() -> None:
    with pytest.raises(ValidationError):
        _make_settings(BYOK_ENCRYPTION_KEY=_known_dev_fernet_key())


def test_gitignore_covers_release_artifacts_but_keeps_samples() -> None:
    text = (_REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    required = {
        ".env",
        ".env.*",
        "!.env.example",
        "!**/.env.example",
        "backend/var/",
        "backend/eval_reports/",
        "__pycache__/",
        ".pytest_cache/",
        ".mypy_cache/",
        ".venv/",
        "node_modules/",
        ".next/",
        "dist/",
        "*.log",
        "*.db",
        "*.sqlite",
        "*.sqlite3",
        "*.pem",
        "*.key",
        "*.p12",
        "*.pfx",
        "*.bak",
        "*.tmp",
    }
    lines = {line.strip() for line in text.splitlines() if line.strip()}
    missing = required - lines
    assert not missing, f"missing .gitignore patterns: {sorted(missing)}"
