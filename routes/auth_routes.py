from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Mapping
from urllib.parse import urljoin, urlsplit

from authlib.integrations.base_client.errors import OAuthError
from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import (
    current_user,
    login_user,
    logout_user,
)

from extensions import db, limiter
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
from services.google_oauth_service import (
    get_google_oauth_client,
)
from services.security.password_service import PasswordService


auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth",
)


# ---------------------------
# Google OAuth errors
# ---------------------------

class GoogleOAuthFlowError(RuntimeError):
    def __init__(
        self,
        code: str,
    ) -> None:
        super().__init__(code)
        self.code = code


# ---------------------------
# Translation helper
# ---------------------------

def translate(
    key: str,
) -> str:
    i18n_service = current_app.extensions[
        "i18n_service"
    ]

    locale = (
        g.get("locale")
        or getattr(
            current_user,
            "locale",
            None,
        )
        or current_app.config[
            "DEFAULT_LOCALE"
        ]
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
        and target_url.scheme
        == reference_url.scheme
        and target_url.netloc
        == reference_url.netloc
    )


# ---------------------------
# OAuth helpers
# ---------------------------

def google_oauth_is_enabled() -> bool:
    return bool(
        current_app.config.get(
            "GOOGLE_OAUTH_ENABLED",
            False,
        )
    )


def normalize_google_email(
    value: Any,
) -> str:
    email = str(
        value or ""
    ).strip().casefold()

    if (
        not email
        or "@" not in email
        or len(email) > 320
    ):
        raise GoogleOAuthFlowError(
            "invalid_google_email"
        )

    return email


def normalize_google_full_name(
    userinfo: Mapping[str, Any],
    email: str,
) -> str:
    raw_name = str(
        userinfo.get("name")
        or email.split(
            "@",
            maxsplit=1,
        )[0]
    )

    full_name = " ".join(
        raw_name.split()
    ).strip()

    if not full_name:
        raise GoogleOAuthFlowError(
            "invalid_google_profile"
        )

    return full_name[:120]


def normalize_google_locale(
    userinfo: Mapping[str, Any],
) -> str:
    supported_locales = tuple(
        current_app.config[
            "SUPPORTED_LOCALES"
        ]
    )

    raw_locale = str(
        userinfo.get("locale")
        or ""
    ).strip()

    normalized_locale = (
        raw_locale
        .replace("_", "-")
        .split("-", maxsplit=1)[0]
        .casefold()
    )

    if normalized_locale in supported_locales:
        return normalized_locale

    browser_locale = (
        request.accept_languages.best_match(
            supported_locales
        )
    )

    return (
        browser_locale
        or current_app.config[
            "DEFAULT_LOCALE"
        ]
    )


def google_email_is_verified(
    value: Any,
) -> bool:
    if value is True:
        return True

    if isinstance(
        value,
        str,
    ):
        return (
            value.strip().casefold()
            == "true"
        )

    return value == 1


def generate_oauth_password() -> str:
    return (
        "Aa1!"
        + secrets.token_urlsafe(48)
    )


# ---------------------------
# Google account resolution
# ---------------------------

def resolve_google_user(
    userinfo: Mapping[str, Any],
):
    google_subject = str(
        userinfo.get("sub")
        or ""
    ).strip()

    if not google_subject:
        raise GoogleOAuthFlowError(
            "invalid_google_profile"
        )

    email = normalize_google_email(
        userinfo.get("email")
    )

    if not google_email_is_verified(
        userinfo.get("email_verified")
    ):
        raise GoogleOAuthFlowError(
            "google_email_not_verified"
        )

    full_name = normalize_google_full_name(
        userinfo,
        email,
    )

    locale = normalize_google_locale(
        userinfo
    )

    user_repository = UserRepository()

    user = user_repository.get_by_email(
        email
    )

    if user is not None:
        if not user.is_active:
            raise GoogleOAuthFlowError(
                "account_disabled"
            )

        if user.email_verified_at is None:
            user.email_verified_at = (
                datetime.now(
                    timezone.utc
                )
            )

            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise

        return user, None

    auth_service = create_auth_service()

    try:
        registration = auth_service.register(
            full_name=full_name,
            organization_name=full_name,
            email=email,
            password=generate_oauth_password(),
            locale=locale,
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
        db.session.rollback()

        if exc.code != "email_already_registered":
            raise GoogleOAuthFlowError(
                "google_registration_failed"
            ) from exc

        user = user_repository.get_by_email(
            email
        )

        if user is None:
            raise GoogleOAuthFlowError(
                "google_registration_failed"
            ) from exc

        if not user.is_active:
            raise GoogleOAuthFlowError(
                "account_disabled"
            ) from exc

        return user, None

    user = registration.user

    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(
            timezone.utc
        )

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    return (
        user,
        str(
            registration.project.id
        ),
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
            db.session.rollback()

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

    return render_template(
        "auth/register.html",
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
            db.session.rollback()

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
                "next",
                type=str,
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

    return render_template(
        "auth/login.html",
        form=form,
    )


# ---------------------------
# Google OAuth start
# ---------------------------

@auth_bp.get("/google")
@limiter.limit("20 per hour")
def google_login():
    if current_user.is_authenticated:
        return redirect(
            url_for(
                "dashboard.index"
            )
        )

    if not google_oauth_is_enabled():
        flash(
            translate(
                "auth.messages.google_not_configured"
            ),
            "warning",
        )

        return redirect(
            url_for(
                "auth.login"
            )
        )

    next_url = request.args.get(
        "next",
        type=str,
    )

    if is_safe_redirect_url(
        next_url
    ):
        session[
            "google_oauth_next"
        ] = next_url
    else:
        session.pop(
            "google_oauth_next",
            None,
        )

    google_client = (
        get_google_oauth_client()
    )

    callback_path = url_for(
        "auth.google_callback",
    )

    public_base_url = current_app.config[
        "PUBLIC_BASE_URL"
    ].rstrip("/")

    callback_url = (
        f"{public_base_url}{callback_path}"
    )

    nonce = secrets.token_urlsafe(32)

    return google_client.authorize_redirect(
        callback_url,
        nonce=nonce,
        prompt="select_account",
    )


# ---------------------------
# Google OAuth callback
# ---------------------------

@auth_bp.get("/google/callback")
@limiter.limit("30 per hour")
def google_callback():
    if not google_oauth_is_enabled():
        flash(
            translate(
                "auth.messages.google_not_configured"
            ),
            "warning",
        )

        return redirect(
            url_for(
                "auth.login"
            )
        )

    provider_error = request.args.get(
        "error",
        type=str,
    )

    if provider_error:
        current_app.logger.warning(
            "Google OAuth refused: %s",
            provider_error,
        )

        session.pop(
            "google_oauth_next",
            None,
        )

        flash(
            translate(
                "auth.messages.google_auth_failed"
            ),
            "danger",
        )

        return redirect(
            url_for(
                "auth.login"
            )
        )

    try:
        google_client = (
            get_google_oauth_client()
        )

        token = (
            google_client
            .authorize_access_token()
        )

        raw_userinfo = token.get(
            "userinfo"
        )

        if not isinstance(
            raw_userinfo,
            Mapping,
        ):
            raise GoogleOAuthFlowError(
                "invalid_google_profile"
            )

        userinfo = dict(
            raw_userinfo
        )

        user, active_project_id = (
            resolve_google_user(
                userinfo
            )
        )

    except OAuthError:
        db.session.rollback()

        current_app.logger.warning(
            "Google OAuth callback rejected.",
            exc_info=True,
        )

        flash(
            translate(
                "auth.messages.google_auth_failed"
            ),
            "danger",
        )

        return redirect(
            url_for(
                "auth.login"
            )
        )

    except GoogleOAuthFlowError as exc:
        db.session.rollback()

        translation_keys = {
            "google_email_not_verified": (
                "auth.messages.google_email_not_verified"
            ),
            "account_disabled": (
                "auth.messages.account_disabled"
            ),
            "invalid_google_email": (
                "auth.messages.google_auth_failed"
            ),
            "invalid_google_profile": (
                "auth.messages.google_auth_failed"
            ),
            "google_registration_failed": (
                "auth.messages.google_registration_failed"
            ),
        }

        flash(
            translate(
                translation_keys.get(
                    exc.code,
                    "auth.messages.google_auth_failed",
                )
            ),
            "danger",
        )

        return redirect(
            url_for(
                "auth.login"
            )
        )

    except Exception:
        db.session.rollback()

        current_app.logger.exception(
            "Unexpected Google OAuth error."
        )

        flash(
            translate(
                "auth.messages.google_auth_failed"
            ),
            "danger",
        )

        return redirect(
            url_for(
                "auth.login"
            )
        )

    next_url = session.pop(
        "google_oauth_next",
        None,
    )

    session.clear()

    login_user(
        user,
        remember=True,
        fresh=True,
    )

    if active_project_id:
        session[
            "active_project_id"
        ] = active_project_id

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