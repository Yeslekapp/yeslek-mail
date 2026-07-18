from __future__ import annotations

import os
from datetime import timedelta
from typing import Final

from dotenv import load_dotenv


# ---------------------------
# Environment loading
# ---------------------------

load_dotenv()


# ---------------------------
# Environment constants
# ---------------------------

TRUE_VALUES: Final[frozenset[str]] = frozenset(
    {
        "1",
        "true",
        "yes",
        "on",
    }
)


# ---------------------------
# Environment helpers
# ---------------------------

def env_string(
    name: str,
    default: str = "",
) -> str:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip()


def env_bool(
    name: str,
    default: bool = False,
) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in TRUE_VALUES


def env_int(
    name: str,
    default: int,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    raw_value = env_string(
        name,
        str(default),
    )

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(
            f"La variable {name} doit être un nombre entier."
        ) from exc

    if minimum is not None and value < minimum:
        raise RuntimeError(
            f"La variable {name} doit être supérieure "
            f"ou égale à {minimum}."
        )

    if maximum is not None and value > maximum:
        raise RuntimeError(
            f"La variable {name} doit être inférieure "
            f"ou égale à {maximum}."
        )

    return value


def env_csv(
    name: str,
    default: str,
) -> tuple[str, ...]:
    raw_value = env_string(
        name,
        default,
    )

    return tuple(
        item.strip()
        for item in raw_value.split(",")
        if item.strip()
    )


# ---------------------------
# Base configuration
# ---------------------------

class BaseConfig:
    APP_NAME = env_string(
        "APP_NAME",
        "Yeslek Mail",
    )

    APP_ENV = env_string(
        "APP_ENV",
        "development",
    ).lower()

    SECRET_KEY = env_string(
        "SECRET_KEY",
        "development-only-change-this-secret",
    )

    PUBLIC_BASE_URL = env_string(
        "PUBLIC_BASE_URL",
        "http://localhost:5000",
    ).rstrip("/")

    SERVER_NAME = (
        env_string(
            "SERVER_NAME",
            "",
        )
        or None
    )

    PREFERRED_URL_SCHEME = env_string(
        "PREFERRED_URL_SCHEME",
        "http",
    )

    MAX_CONTENT_LENGTH = env_int(
        "MAX_CONTENT_LENGTH",
        2 * 1024 * 1024,
        minimum=1024,
    )

    JSON_SORT_KEYS = False
    PROPAGATE_EXCEPTIONS = False


# ---------------------------
# PostgreSQL
# ---------------------------

    SQLALCHEMY_DATABASE_URI = env_string(
        "DATABASE_URL",
        (
            "postgresql+psycopg://yeslek:"
            "yeslek_password@localhost:5432/yeslek_mail"
        ),
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": env_int(
            "DATABASE_POOL_RECYCLE_SECONDS",
            300,
            minimum=30,
            maximum=86400,
        ),
        "pool_size": env_int(
            "DATABASE_POOL_SIZE",
            10,
            minimum=1,
            maximum=100,
        ),
        "max_overflow": env_int(
            "DATABASE_MAX_OVERFLOW",
            20,
            minimum=0,
            maximum=200,
        ),
        "pool_timeout": env_int(
            "DATABASE_POOL_TIMEOUT_SECONDS",
            30,
            minimum=1,
            maximum=300,
        ),
    }


# ---------------------------
# Redis
# ---------------------------

    REDIS_URL = env_string(
        "REDIS_URL",
        "redis://localhost:6379/0",
    )

    SESSION_REDIS_URL = env_string(
        "SESSION_REDIS_URL",
        "redis://localhost:6379/1",
    )

    CELERY_BROKER_URL = env_string(
        "CELERY_BROKER_URL",
        "redis://localhost:6379/2",
    )

    CELERY_RESULT_BACKEND = env_string(
        "CELERY_RESULT_BACKEND",
        "redis://localhost:6379/3",
    )


# ---------------------------
# Celery
# ---------------------------

    CELERY = {
        "broker_url": CELERY_BROKER_URL,
        "result_backend": CELERY_RESULT_BACKEND,
        "task_serializer": "json",
        "accept_content": [
            "json",
        ],
        "result_serializer": "json",
        "timezone": "UTC",
        "enable_utc": True,
        "task_track_started": True,
        "task_acks_late": True,
        "task_reject_on_worker_lost": True,
        "worker_prefetch_multiplier": 1,
        "broker_connection_retry_on_startup": True,
        "task_default_queue": "yeslek-mail",
        "task_routes": {
            "workers.email_worker.*": {
                "queue": "email-delivery",
            },
            "workers.webhook_worker.*": {
                "queue": "webhook-delivery",
            },
        },
    }


# ---------------------------
# Server-side sessions
# ---------------------------

    SESSION_TYPE = "redis"
    SESSION_USE_SIGNER = True
    SESSION_PERMANENT = True
    SESSION_REFRESH_EACH_REQUEST = True
    SESSION_KEY_PREFIX = "yeslek:session:"

    PERMANENT_SESSION_LIFETIME = timedelta(
        hours=env_int(
            "SESSION_LIFETIME_HOURS",
            12,
            minimum=1,
            maximum=720,
        )
    )

    SESSION_COOKIE_NAME = env_string(
        "SESSION_COOKIE_NAME",
        "yeslek_session",
    )

    SESSION_COOKIE_HTTPONLY = True

    SESSION_COOKIE_SAMESITE = env_string(
        "SESSION_COOKIE_SAMESITE",
        "Lax",
    )

    SESSION_COOKIE_SECURE = env_bool(
        "SESSION_COOKIE_SECURE",
        False,
    )


# ---------------------------
# Remember-me cookie
# ---------------------------

    REMEMBER_COOKIE_NAME = env_string(
        "REMEMBER_COOKIE_NAME",
        "yeslek_remember",
    )

    REMEMBER_COOKIE_HTTPONLY = True

    REMEMBER_COOKIE_SAMESITE = env_string(
        "REMEMBER_COOKIE_SAMESITE",
        "Lax",
    )

    REMEMBER_COOKIE_SECURE = env_bool(
        "REMEMBER_COOKIE_SECURE",
        False,
    )

    REMEMBER_COOKIE_DURATION = timedelta(
        days=env_int(
            "REMEMBER_COOKIE_DAYS",
            30,
            minimum=1,
            maximum=365,
        )
    )


# ---------------------------
# CSRF protection
# ---------------------------

    WTF_CSRF_ENABLED = True

    WTF_CSRF_TIME_LIMIT = timedelta(
        hours=env_int(
            "CSRF_TOKEN_LIFETIME_HOURS",
            2,
            minimum=1,
            maximum=24,
        )
    )

    WTF_CSRF_SSL_STRICT = env_bool(
        "WTF_CSRF_SSL_STRICT",
        False,
    )


# ---------------------------
# Authentication
# ---------------------------

    PASSWORD_MIN_LENGTH = env_int(
        "PASSWORD_MIN_LENGTH",
        12,
        minimum=8,
        maximum=128,
    )

    PASSWORD_MAX_LENGTH = env_int(
        "PASSWORD_MAX_LENGTH",
        128,
        minimum=12,
        maximum=1024,
    )

    EMAIL_VERIFICATION_TOKEN_TTL_SECONDS = env_int(
        "EMAIL_VERIFICATION_TOKEN_TTL_SECONDS",
        86400,
        minimum=300,
        maximum=604800,
    )

    PASSWORD_RESET_TOKEN_TTL_SECONDS = env_int(
        "PASSWORD_RESET_TOKEN_TTL_SECONDS",
        3600,
        minimum=300,
        maximum=86400,
    )


# ---------------------------
# API keys
# ---------------------------

    API_KEY_PREFIX = env_string(
        "API_KEY_PREFIX",
        "yeslek_live_",
    )

    API_KEY_TEST_PREFIX = env_string(
        "API_KEY_TEST_PREFIX",
        "yeslek_test_",
    )

    API_KEY_PEPPER = env_string(
        "API_KEY_PEPPER",
        "development-only-change-this-api-key-pepper",
    )


# ---------------------------
# SMTP
# ---------------------------

    SMTP_HOST = env_string(
        "SMTP_HOST",
        "localhost",
    )

    SMTP_PORT = env_int(
        "SMTP_PORT",
        1025,
        minimum=1,
        maximum=65535,
    )

    SMTP_USERNAME = env_string(
        "SMTP_USERNAME",
        "",
    )

    SMTP_PASSWORD = env_string(
        "SMTP_PASSWORD",
        "",
    )

    SMTP_USE_TLS = env_bool(
        "SMTP_USE_TLS",
        False,
    )

    SMTP_USE_SSL = env_bool(
        "SMTP_USE_SSL",
        False,
    )

    SMTP_TIMEOUT_SECONDS = env_int(
        "SMTP_TIMEOUT_SECONDS",
        20,
        minimum=1,
        maximum=300,
    )

    MAIL_DEFAULT_SENDER_EMAIL = env_string(
        "MAIL_DEFAULT_SENDER_EMAIL",
        "notifications@yeslek.local",
    )

    MAIL_DEFAULT_SENDER_NAME = env_string(
        "MAIL_DEFAULT_SENDER_NAME",
        "Yeslek Mail",
    )

    MAIL_MESSAGE_ID_DOMAIN = env_string(
        "MAIL_MESSAGE_ID_DOMAIN",
        "yeslek.local",
    )

    MAIL_RETURN_PATH_DOMAIN = env_string(
        "MAIL_RETURN_PATH_DOMAIN",
        "bounce.yeslek.local",
    )


# ---------------------------
# Email delivery
# ---------------------------

    EMAIL_MAX_ATTEMPTS = env_int(
        "EMAIL_MAX_ATTEMPTS",
        5,
        minimum=1,
        maximum=20,
    )

    EMAIL_SUBJECT_MAX_LENGTH = 998

    EMAIL_HTML_MAX_LENGTH = env_int(
        "EMAIL_HTML_MAX_LENGTH",
        1024 * 1024,
        minimum=1024,
    )

    EMAIL_TEXT_MAX_LENGTH = env_int(
        "EMAIL_TEXT_MAX_LENGTH",
        512 * 1024,
        minimum=1024,
    )


# ---------------------------
# Account plan
# ---------------------------

    DEFAULT_MONTHLY_EMAIL_LIMIT = env_int(
        "DEFAULT_MONTHLY_EMAIL_LIMIT",
        300,
        minimum=1,
        maximum=100_000_000,
    )


# ---------------------------
# Rate limiting
# ---------------------------

    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI = REDIS_URL
    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_STRATEGY = "fixed-window"

    AUTH_LOGIN_RATE_LIMIT = env_string(
        "AUTH_LOGIN_RATE_LIMIT",
        "10 per minute",
    )

    AUTH_REGISTER_RATE_LIMIT = env_string(
        "AUTH_REGISTER_RATE_LIMIT",
        "5 per hour",
    )

    API_EMAIL_SEND_RATE_LIMIT = env_string(
        "API_EMAIL_SEND_RATE_LIMIT",
        "120 per minute",
    )


# ---------------------------
# Internationalization
# ---------------------------

    DEFAULT_LOCALE = env_string(
        "DEFAULT_LOCALE",
        "fr",
    )

    SUPPORTED_LOCALES = env_csv(
        "SUPPORTED_LOCALES",
        "fr,en",
    )


# ---------------------------
# Proxy configuration
# ---------------------------

    TRUST_PROXY_HEADERS = env_bool(
        "TRUST_PROXY_HEADERS",
        False,
    )


# ---------------------------
# Security headers
# ---------------------------

    CONTENT_SECURITY_POLICY = env_string(
        "CONTENT_SECURITY_POLICY",
        (
            "default-src 'self'; "
            "img-src 'self' data: https:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        ),
    )

    REFERRER_POLICY = env_string(
        "REFERRER_POLICY",
        "strict-origin-when-cross-origin",
    )

    PERMISSIONS_POLICY = env_string(
        "PERMISSIONS_POLICY",
        "camera=(), microphone=(), geolocation=()",
    )


# ---------------------------
# Logging
# ---------------------------

    LOG_LEVEL = env_string(
        "LOG_LEVEL",
        "INFO",
    ).upper()


# ---------------------------
# Configuration validation
# ---------------------------

    @classmethod
    def validate(cls) -> None:
        if cls.SMTP_USE_TLS and cls.SMTP_USE_SSL:
            raise RuntimeError(
                "SMTP_USE_TLS et SMTP_USE_SSL "
                "ne peuvent pas être activés ensemble."
            )


# ---------------------------
# Development configuration
# ---------------------------

class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TESTING = False

    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    WTF_CSRF_SSL_STRICT = False
    TRUST_PROXY_HEADERS = False


# ---------------------------
# Testing configuration
# ---------------------------

class TestingConfig(BaseConfig):
    DEBUG = False
    TESTING = True

    SQLALCHEMY_DATABASE_URI = env_string(
        "TEST_DATABASE_URL",
        (
            "postgresql+psycopg://yeslek:"
            "yeslek_password@localhost:5432/yeslek_mail_test"
        ),
    )

    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    RATELIMIT_ENABLED = False

    CELERY = {
        **BaseConfig.CELERY,
        "task_always_eager": True,
        "task_eager_propagates": True,
    }


# ---------------------------
# Production configuration
# ---------------------------

class ProductionConfig(BaseConfig):
    DEBUG = False
    TESTING = False

    PREFERRED_URL_SCHEME = "https"

    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    WTF_CSRF_SSL_STRICT = True
    TRUST_PROXY_HEADERS = True

    @classmethod
    def validate(cls) -> None:
        super().validate()

        unsafe_values = {
            "SECRET_KEY": cls.SECRET_KEY,
            "API_KEY_PEPPER": cls.API_KEY_PEPPER,
        }

        invalid_names = [
            name
            for name, value in unsafe_values.items()
            if (
                len(value) < 32
                or "development-only" in value
                or "change-this" in value
            )
        ]

        if invalid_names:
            raise RuntimeError(
                "Configuration de production non sécurisée : "
                + ", ".join(invalid_names)
            )

        if not cls.SQLALCHEMY_DATABASE_URI.startswith(
            "postgresql"
        ):
            raise RuntimeError(
                "PostgreSQL est obligatoire en production."
            )

        if not cls.PUBLIC_BASE_URL.startswith(
            "https://"
        ):
            raise RuntimeError(
                "PUBLIC_BASE_URL doit utiliser HTTPS "
                "en production."
            )


# ---------------------------
# Configuration resolver
# ---------------------------

CONFIG_BY_ENVIRONMENT = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config_class(
    environment: str | None = None,
) -> type[BaseConfig]:
    selected_environment = (
        environment
        or env_string(
            "APP_ENV",
            "development",
        )
    ).strip().lower()

    config_class = CONFIG_BY_ENVIRONMENT.get(
        selected_environment
    )

    if config_class is None:
        allowed_values = ", ".join(
            sorted(
                CONFIG_BY_ENVIRONMENT.keys()
            )
        )

        raise RuntimeError(
            f"APP_ENV invalide : {selected_environment}. "
            f"Valeurs autorisées : {allowed_values}."
        )

    return config_class