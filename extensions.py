from __future__ import annotations

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect


# ---------------------------
# PostgreSQL
# ---------------------------

db = SQLAlchemy()


# ---------------------------
# Database migrations
# ---------------------------

migrate = Migrate(
    compare_type=True,
)


# ---------------------------
# Authentication
# ---------------------------

login_manager = LoginManager()


# ---------------------------
# CSRF protection
# ---------------------------

csrf = CSRFProtect()


# ---------------------------
# Server-side sessions
# ---------------------------

session_manager = Session()


# ---------------------------
# Rate limiting
# ---------------------------

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    headers_enabled=True,
)