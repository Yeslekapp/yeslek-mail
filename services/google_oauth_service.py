from __future__ import annotations

from typing import Any

from authlib.integrations.flask_client import OAuth
from flask import Flask, current_app


# ---------------------------
# Google OpenID Connect
# ---------------------------

GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/"
    ".well-known/openid-configuration"
)


# ---------------------------
# OAuth initialization
# ---------------------------

def init_google_oauth(
    app: Flask,
) -> None:
    oauth_registry = OAuth(
        app
    )

    app.extensions[
        "oauth_registry"
    ] = oauth_registry

    if not app.config.get(
        "GOOGLE_OAUTH_ENABLED",
        False,
    ):
        app.logger.info(
            "Google OAuth is disabled."
        )
        return

    client_id = str(
        app.config.get(
            "GOOGLE_CLIENT_ID",
            "",
        )
    ).strip()

    client_secret = str(
        app.config.get(
            "GOOGLE_CLIENT_SECRET",
            "",
        )
    ).strip()

    if not client_id:
        raise RuntimeError(
            "GOOGLE_CLIENT_ID est absent."
        )

    if not client_secret:
        raise RuntimeError(
            "GOOGLE_CLIENT_SECRET est absent."
        )

    oauth_registry.register(
        name="google",
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url=(
            GOOGLE_DISCOVERY_URL
        ),
        client_kwargs={
            "scope": (
                "openid profile email"
            ),
        },
    )

    app.logger.info(
        "Google OAuth client configured."
    )


# ---------------------------
# OAuth client access
# ---------------------------

def get_google_oauth_client() -> Any:
    oauth_registry = (
        current_app.extensions.get(
            "oauth_registry"
        )
    )

    if oauth_registry is None:
        raise RuntimeError(
            "Le registre OAuth "
            "n'est pas initialisé."
        )

    google_client = (
        oauth_registry.create_client(
            "google"
        )
    )

    if google_client is None:
        raise RuntimeError(
            "Le client Google OAuth "
            "n'est pas configuré."
        )

    return google_client