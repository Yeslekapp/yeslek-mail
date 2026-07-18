from __future__ import annotations

from urllib.parse import urljoin, urlsplit

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    request,
    session,
    url_for,
)
from flask_login import (
    current_user,
    login_user,
    logout_user,
)

from extensions import limiter
from forms.auth_forms import LoginForm, RegisterForm
from repositories.organization_repository import (
    OrganizationRepository,
)
from repositories.project_repository import (
    ProjectRepository,
)
from repositories.user_repository import UserRepository
from services.auth_service import (
    AuthService,
    AuthServiceError,
)
from services.security.password_service import PasswordService


auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth",
)


# ---------------------------
# Translation helper
# ---------------------------

def translate(
    key: str,
) -> str:
    i18n_service = current_app.extensions[
        "i18n_service"
    ]

    locale = getattr(
        current_user,
        "locale",
        current_app.config["DEFAULT_LOCALE"],
    )

    return i18n_service.get(
        key=key,
        locale=locale,
    )


# ---------------------------
# Authentication service factory
# ---------------------------

def create_auth_service() -> AuthService:
    return AuthService(
        user_repository=UserRepository(),
        organization_repository=(
            OrganizationRepository()
        ),
        project_repository=ProjectRepository(),
        password_service=PasswordService(),
    )


# ---------------------------
# Safe redirect validation
# ---------------------------

def is_safe_redirect_url(
    target: str | None,
) -> bool:
    if not target:
        return False

    reference_url = urlsplit(
        request.host_url
    )

    target_url = urlsplit(
        urljoin(
            request.host_url,
            target,
        )
    )

    return (
        target_url.scheme
        in {
            "http",
            "https",
        }
        and target_url.netloc
        == reference_url.netloc
    )


# ---------------------------
# Registration
# ---------------------------

@auth_bp.route(
    "/register",
    methods=[
        "GET",
        "POST",
    ],
)
@limiter.limit("5 per hour")
def register():
    if current_user.is_authenticated:
        return redirect(
            url_for(
                "dashboard.index"
            )
        )

    form = RegisterForm()

    if form.validate_on_submit():
        auth_service = create_auth_service()

        try:
            registration = auth_service.register(
                full_name=form.full_name.data,
                organization_name=(
                    form.organization_name.data
                ),
                email=form.email.data,
                password=form.password.data,
                locale=(
                    request.accept_languages.best_match(
                        current_app.config[
                            "SUPPORTED_LOCALES"
                        ]
                    )
                    or current_app.config[
                        "DEFAULT_LOCALE"
                    ]
                ),
                default_sender_email=(
                    current_app.config[
                        "MAIL_DEFAULT_SENDER_EMAIL"
                    ]
                ),
                default_sender_name=(
                    current_app.config[
                        "MAIL_DEFAULT_SENDER_NAME"
                    ]
                ),
            )

        except AuthServiceError as exc:
            error_messages = {
                "email_already_registered": (
                    "auth.messages.email_already_registered"
                ),
                "invalid_email": (
                    "auth.messages.invalid_email"
                ),
                "invalid_name": (
                    "auth.messages.invalid_name"
                ),
                "name_too_long": (
                    "auth.messages.name_too_long"
                ),
                "password_too_short": (
                    "auth.messages.password_too_short"
                ),
                "password_too_long": (
                    "auth.messages.password_too_long"
                ),
                "password_not_complex_enough": (
                    "auth.messages.password_not_complex"
                ),
                "registration_conflict": (
                    "auth.messages.registration_conflict"
                ),
            }

            translation_key = error_messages.get(
                exc.code,
                "auth.messages.registration_failed",
            )

            flash(
                translate(
                    translation_key
                ),
                "danger",
            )

        except Exception:
            current_app.logger.exception(
                "Unexpected registration error."
            )

            flash(
                translate(
                    "auth.messages.registration_failed"
                ),
                "danger",
            )

        else:
            session.clear()

            login_user(
                registration.user,
                remember=False,
                fresh=True,
            )

            session[
                "active_project_id"
            ] = str(
                registration.project.id
            )

            flash(
                translate(
                    "auth.messages.account_created"
                ),
                "success",
            )

            return redirect(
                url_for(
                    "dashboard.index"
                )
            )

    return current_app.jinja_env.get_or_select_template(
        "auth/register.html"
    ).render(
        form=form,
    )


# ---------------------------
# Login
# ---------------------------

@auth_bp.route(
    "/login",
    methods=[
        "GET",
        "POST",
    ],
)
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(
            url_for(
                "dashboard.index"
            )
        )

    form = LoginForm()

    if form.validate_on_submit():
        auth_service = create_auth_service()

        try:
            user = auth_service.authenticate(
                email=form.email.data,
                password=form.password.data,
            )

        except Exception:
            current_app.logger.exception(
                "Unexpected authentication error."
            )

            user = None

        if user is None:
            flash(
                translate(
                    "auth.messages.invalid_credentials"
                ),
                "danger",
            )

        else:
            next_url = request.args.get(
                "next"
            )

            session.clear()

            login_user(
                user,
                remember=bool(
                    form.remember_me.data
                ),
                fresh=True,
            )

            flash(
                translate(
                    "auth.messages.login_success"
                ),
                "success",
            )

            if is_safe_redirect_url(
                next_url
            ):
                return redirect(
                    next_url
                )

            return redirect(
                url_for(
                    "dashboard.index"
                )
            )

    return current_app.jinja_env.get_or_select_template(
        "auth/login.html"
    ).render(
        form=form,
    )


# ---------------------------
# Logout
# ---------------------------

@auth_bp.post("/logout")
@limiter.limit("30 per hour")
def logout():
    logout_user()
    session.clear()

    flash(
        translate(
            "auth.messages.logged_out"
        ),
        "info",
    )

    return redirect(
        url_for(
            "auth.login"
        )
    )