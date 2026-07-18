from __future__ import annotations

from flask import Flask
from redis import Redis


def create_redis_client(
    url: str,
    *,
    decode_responses: bool,
) -> Redis:
    redis_url = (url or "").strip()

    if not redis_url:
        raise RuntimeError(
            "L'URL Redis est absente de Cloud Run."
        )

    if not redis_url.startswith(
        (
            "redis://",
            "rediss://",
            "unix://",
        )
    ):
        raise RuntimeError(
            "L'URL Redis doit commencer par "
            "redis:// ou rediss://."
        )

    return Redis.from_url(
        redis_url,
        decode_responses=decode_responses,
        socket_connect_timeout=5,
        socket_timeout=5,
        health_check_interval=30,
    )


def configure_redis_clients(
    app: Flask,
) -> None:
    session_redis = create_redis_client(
        app.config["SESSION_REDIS_URL"],
        decode_responses=False,
    )

    general_redis = create_redis_client(
        app.config["REDIS_URL"],
        decode_responses=True,
    )

    app.config["SESSION_REDIS"] = session_redis
    app.extensions["redis"] = general_redis