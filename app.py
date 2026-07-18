from __future__ import annotations

import logging
import uuid
from pathlib import Path

from flask import (
    Flask,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user
from flask_wtf.csrf import CSRFError
from redis import Redis
from sqlalchemy import text
from werkzeug.middleware.proxy_fix import ProxyFix

from celery_app import init_celery
from config import get_config_class
from extensions import (
    csrf,
    db,
    limiter,
    login_manager,
    migrate,
    session_manager,
)
from services.i18n_service import I18nService


# ---------------------------
# Application factory
# ---------------------------

def create_app(
    environment: str | None = None,
) -> Flask:
    config_class = get_config_class(
        environment
    )

    app = Flask(
        __name__,
        instance_relative_config=True,
    )

    app.config.from_object(
        config_class
    )

    config_class.validate()

    Path(
        app.instance_path
    ).mkdir(
        parents=True,
        exist_ok=True,
    )

    configure_proxy(app)
    configure_logging(app)
    configure_redis(app)
    initialize_extensions(app)
    initialize_models()
    initialize_i18n(app)
    register_routes(app)
    register_login_handlers(app)
    register_request_handlers(app)
    register_error_handlers(app)
    register_application_routes(app)

    return app


# ---------------------------
# Reverse proxy
# ---------------------------

def configure_proxy(
    app: Flask,
) -> None:
    if not app.config[
        "TRUST_PROXY_HEADERS"
    ]:
        return

    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
        x_port=1,
    )


# ---------------------------
# Logging
# ---------------------------

def configure_logging(
    app: Flask,
) -> None:
    log_level_name = app.config.get(
        "LOG_LEVEL",
        "INFO",
    )

    log_level = getattr(
        logging,
        log_level_name,
        logging.INFO,
    )

    logging.basicConfig(
        level=log_level,
        format=(
            "%(asctime)s "
            "%(levelname)s "
            "%(name)s "
            "%(message)s"
        ),
    )

    app.logger.setLevel(
        log_level
    )


# ---------------------------
# Redis
# ---------------------------

def configure_redis(
    app: Flask,
) -> None:
    session_redis = Redis.from_url(
        app.config[
            "SESSION_REDIS_URL"
        ],
        decode_responses=False,
        socket_connect_timeout=5,
        socket_timeout=5,
        health_check_interval=30,
    )

    general_redis = Redis.from_url(
        app.config[
            "REDIS_URL"
        ],
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        health_check_interval=30,
    )

    app.config[
        "SESSION_REDIS"
    ] = session_redis

    app.extensions[
        "redis"
    ] = general_redis


# ---------------------------
# Flask extensions
# ---------------------------

def initialize_extensions(
    app: Flask,
) -> None:
    db.init_app(app)

    migrate.init_app(
        app,
        db,
        compare_type=True,
    )

    login_manager.init_app(app)
    csrf.init_app(app)
    session_manager.init_app(app)
    limiter.init_app(app)

    init_celery(app)


# ---------------------------
# SQLAlchemy model registration
# ---------------------------

def initialize_models() -> None:
    import models

    _ = models


# ---------------------------
# Internationalization
# ---------------------------

def initialize_i18n(
    app: Flask,
) -> None:
    i18n_service = I18nService(
        directory=(
            Path(app.root_path)
            / "l10n"
        ),
        default_locale=app.config[
            "DEFAULT_LOCALE"
        ],
        supported_locales=app.config[
            "SUPPORTED_LOCALES"
        ],
    )

    app.extensions[
        "i18n_service"
    ] = i18n_service

    @app.context_processor
    def inject_translation_helpers():
        def translate(
            key: str,
            locale: str | None = None,
        ) -> str:
            selected_locale = (
                locale
                or g.get(
                    "locale"
                )
                or app.config[
                    "DEFAULT_LOCALE"
                ]
            )

            return i18n_service.get(
                key=key,
                locale=selected_locale,
            )

        return {
            "app_name": app.config[
                "APP_NAME"
            ],
            "t": translate,
        }



# ---------------------------
# Blueprint registration
# ---------------------------

def register_routes(
    app: Flask,
) -> None:
    import importlib
    import pkgutil

    import routes
    from flask import Blueprint

    registered_blueprints: set[str] = set()

    for module_info in pkgutil.iter_modules(
        routes.__path__
    ):
        module_name = module_info.name

        if module_name.startswith("_"):
            continue

        if not module_name.endswith("_routes"):
            continue

        module = importlib.import_module(
            f"routes.{module_name}"
        )

        for value in vars(module).values():
            if not isinstance(value, Blueprint):
                continue

            if value.name in registered_blueprints:
                continue

            app.register_blueprint(value)
            registered_blueprints.add(value.name)

            app.logger.info(
                "Blueprint enregistré : %s",
                value.name,
            )

    if not registered_blueprints:
        raise RuntimeError(
            "Aucun Blueprint trouvé dans "
            "routes/*_routes.py"
        )


# ---------------------------
# Login manager
# ---------------------------

def register_login_handlers(
    app: Flask,
) -> None:
    from models.user import User

    login_manager.login_view = "auth.login"

    login_manager.login_message = (
        "Veuillez vous connecter "
        "pour continuer."
    )

    login_manager.login_message_category = (
        "warning"
    )

    @login_manager.user_loader
    def load_user(
        user_id: str,
    ) -> User | None:
        try:
            parsed_user_id = uuid.UUID(
                user_id
            )
        except (
            TypeError,
            ValueError,
        ):
            return None

        return db.session.get(
            User,
            parsed_user_id,
        )

    @login_manager.unauthorized_handler
    def unauthorized():
        if is_api_request():
            return jsonify(
                {
                    "error": {
                        "code": "authentication_required",
                        "message": (
                            "Une authentification "
                            "est obligatoire."
                        ),
                        "request_id": g.get(
                            "request_id"
                        ),
                    }
                }
            ), 401

        flash(
            "Veuillez vous connecter "
            "pour continuer.",
            "warning",
        )

        return redirect(
            url_for(
                "auth.login",
                next=request.full_path,
            )
        )


# ---------------------------
# Request handlers
# ---------------------------

def register_request_handlers(
    app: Flask,
) -> None:
    @app.before_request
    def prepare_request_context() -> None:
        request_id = request.headers.get(
            "X-Request-ID",
            "",
        ).strip()

        if not request_id:
            request_id = str(
                uuid.uuid4()
            )

        g.request_id = request_id

        user_locale = None

        if current_user.is_authenticated:
            user_locale = getattr(
                current_user,
                "locale",
                None,
            )

        browser_locale = (
            request.accept_languages.best_match(
                app.config[
                    "SUPPORTED_LOCALES"
                ]
            )
        )

        g.locale = (
            user_locale
            or browser_locale
            or app.config[
                "DEFAULT_LOCALE"
            ]
        )

    @app.after_request
    def add_response_headers(response):
        response.headers[
            "X-Request-ID"
        ] = g.get(
            "request_id",
            "",
        )

        response.headers[
            "X-Content-Type-Options"
        ] = "nosniff"

        response.headers[
            "X-Frame-Options"
        ] = "DENY"

        response.headers[
            "Referrer-Policy"
        ] = app.config[
            "REFERRER_POLICY"
        ]

        response.headers[
            "Permissions-Policy"
        ] = app.config[
            "PERMISSIONS_POLICY"
        ]

        response.headers[
            "Content-Security-Policy"
        ] = app.config[
            "CONTENT_SECURITY_POLICY"
        ]

        if app.config[
            "APP_ENV"
        ] == "production":
            response.headers[
                "Strict-Transport-Security"
            ] = (
                "max-age=31536000; "
                "includeSubDomains"
            )

        if request.path.startswith(
            "/auth/"
        ):
            response.headers[
                "Cache-Control"
            ] = (
                "no-store, "
                "no-cache, "
                "must-revalidate, "
                "private"
            )

        return response


# ---------------------------
# Application routes
# ---------------------------

def register_application_routes(
    app: Flask,
) -> None:
    @app.get("/")
    def index():
        if current_user.is_authenticated:
            return redirect(
                url_for(
                    "dashboard.index"
                )
            )

        return redirect(
            url_for(
                "auth.login"
            )
        )

    @app.get("/health")
    def health():
        checks = {
            "database": False,
            "redis": False,
        }

        try:
            db.session.execute(
                text("SELECT 1")
            )

            checks[
                "database"
            ] = True
        except Exception:
            db.session.rollback()

            current_app.logger.exception(
                "Database health check failed."
            )

        try:
            redis_client = current_app.extensions[
                "redis"
            ]

            checks[
                "redis"
            ] = bool(
                redis_client.ping()
            )
        except Exception:
            current_app.logger.exception(
                "Redis health check failed."
            )

        healthy = all(
            checks.values()
        )

        return jsonify(
            {
                "status": (
                    "ok"
                    if healthy
                    else "degraded"
                ),
                "service": current_app.config[
                    "APP_NAME"
                ],
                "environment": current_app.config[
                    "APP_ENV"
                ],
                "checks": checks,
                "request_id": g.get(
                    "request_id"
                ),
            }
        ), (
            200
            if healthy
            else 503
        )


# ---------------------------
# Error handlers
# ---------------------------

def register_error_handlers(
    app: Flask,
) -> None:
    @app.errorhandler(CSRFError)
    def csrf_error(
        error: CSRFError,
    ):
        if is_api_request():
            return jsonify(
                {
                    "error": {
                        "code": "csrf_error",
                        "message": (
                            "Le jeton de sécurité "
                            "est invalide ou expiré."
                        ),
                        "request_id": g.get(
                            "request_id"
                        ),
                    }
                }
            ), 400

        app.logger.warning(
            "CSRF validation failed: %s",
            error.description,
        )

        return render_template(
            "errors/400.html",
        ), 400

    @app.errorhandler(400)
    def bad_request(_error):
        if is_api_request():
            return api_error_response(
                code="bad_request",
                message="La requête est invalide.",
                status_code=400,
            )

        return render_template(
            "errors/400.html",
        ), 400

    @app.errorhandler(403)
    def forbidden(_error):
        if is_api_request():
            return api_error_response(
                code="forbidden",
                message="Accès refusé.",
                status_code=403,
            )

        return render_template(
            "errors/403.html",
        ), 403

    @app.errorhandler(404)
    def not_found(_error):
        if is_api_request():
            return api_error_response(
                code="not_found",
                message="Ressource introuvable.",
                status_code=404,
            )

        return render_template(
            "errors/404.html",
        ), 404

    @app.errorhandler(429)
    def rate_limit_exceeded(_error):
        if is_api_request():
            return api_error_response(
                code="rate_limit_exceeded",
                message=(
                    "Trop de requêtes. "
                    "Veuillez réessayer plus tard."
                ),
                status_code=429,
            )

        return render_template(
            "errors/429.html",
        ), 429

    @app.errorhandler(500)
    def internal_error(
        error,
    ):
        db.session.rollback()

        app.logger.exception(
            "Unhandled application error.",
            exc_info=error,
        )

        if is_api_request():
            return api_error_response(
                code="internal_error",
                message=(
                    "Une erreur interne "
                    "est survenue."
                ),
                status_code=500,
            )

        return render_template(
            "errors/500.html",
        ), 500


# ---------------------------
# API helpers
# ---------------------------

def is_api_request() -> bool:
    return request.path.startswith(
        "/api/"
    )


def api_error_response(
    *,
    code: str,
    message: str,
    status_code: int,
):
    return jsonify(
        {
            "error": {
                "code": code,
                "message": message,
                "request_id": g.get(
                    "request_id"
                ),
            }
        }
    ), status_code


# ---------------------------
# WSGI application
# ---------------------------

app = create_app()