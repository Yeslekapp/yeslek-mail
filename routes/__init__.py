from __future__ import annotations

from flask import Flask

from routes.api_routes import api_bp
from routes.auth_routes import auth_bp
from routes.dashboard_routes import dashboard_bp
from routes.sender_domain_routes import settings_bp


def register_routes(
    app: Flask,
) -> None:
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(settings_bp)