from __future__ import annotations

from typing import Any

from flask import Flask
from redis import Redis
from redis.exceptions import RedisError


# ---------------------------
# Création du client Redis
# ---------------------------

def create_redis_client(
    url: str | None,
    *,
    decode_responses: bool,
) -> Redis:
    redis_url = (url or "").strip()

    if not redis_url:
        raise RuntimeError(
            "L'URL Redis est absente de la configuration."
        )

    allowed_schemes = (
        "redis://",
        "rediss://",
        "unix://",
    )

    if not redis_url.startswith(allowed_schemes):
        raise RuntimeError(
            "L'URL Redis doit commencer par "
            "redis://, rediss:// ou unix://."
        )

    return Redis.from_url(
        redis_url,
        decode_responses=decode_responses,
        socket_connect_timeout=5,
        socket_timeout=5,
        health_check_interval=30,
        retry_on_timeout=True,
    )


# ---------------------------
# Configuration des clients Redis
# ---------------------------

def configure_redis_clients(
    app: Flask,
) -> None:
    general_redis_url = _get_config_value(
        app,
        "REDIS_URL",
    )

    session_redis_url = (
        _get_config_value(
            app,
            "SESSION_REDIS_URL",
            required=False,
        )
        or general_redis_url
    )

    general_redis = create_redis_client(
        general_redis_url,
        decode_responses=True,
    )

    session_redis = create_redis_client(
        session_redis_url,
        decode_responses=False,
    )

    app.config["SESSION_REDIS"] = session_redis
    app.extensions["redis"] = general_redis
    app.extensions["session_redis"] = session_redis

    app.logger.info(
        "Clients Redis configurés."
    )


# ---------------------------
# Lecture sécurisée de la configuration
# ---------------------------

def _get_config_value(
    app: Flask,
    key: str,
    *,
    required: bool = True,
) -> str | None:
    raw_value: Any = app.config.get(key)

    if raw_value is None:
        value = ""
    else:
        value = str(raw_value).strip()

    if required and not value:
        raise RuntimeError(
            f"La variable {key} est absente "
            "de la configuration Cloud Run."
        )

    return value or None