from __future__ import annotations

import re
import secrets
import unicodedata
from dataclasses import dataclass

from email_validator import (
    EmailNotValidError,
    validate_email,
)
from sqlalchemy.exc import IntegrityError

from extensions import db
from models.organization import Organization
from models.organization_member import OrganizationMember
from models.project import Project
from models.user import User
from repositories.organization_repository import (
    OrganizationRepository,
)
from repositories.project_repository import (
    ProjectRepository,
)
from repositories.user_repository import UserRepository
from services.security.password_service import PasswordService


# ---------------------------
# Constants
# ---------------------------

SUPPORTED_LOCALES = frozenset(
    {
        "fr",
        "en",
    }
)

DEFAULT_LOCALE = "fr"

DEFAULT_PROJECT_NAME = (
    "Mon premier projet"
)

DEFAULT_PROJECT_SLUG = (
    "mon-premier-projet"
)


# ---------------------------
# Authentication exceptions
# ---------------------------

class AuthServiceError(Exception):
    def __init__(
        self,
        code: str,
    ) -> None:
        super().__init__(code)

        self.code = code


# ---------------------------
# Registration result
# ---------------------------

@dataclass(
    frozen=True,
    slots=True,
)
class RegistrationResult:
    user: User
    organization: Organization
    project: Project


# ---------------------------
# Authentication service
# ---------------------------

class AuthService:
    def __init__(
        self,
        *,
        user_repository: UserRepository,
        organization_repository: OrganizationRepository,
        project_repository: ProjectRepository,
        password_service: PasswordService,
    ) -> None:
        self._user_repository = (
            user_repository
        )

        self._organization_repository = (
            organization_repository
        )

        self._project_repository = (
            project_repository
        )

        self._password_service = (
            password_service
        )

    # ---------------------------
    # Registration
    # ---------------------------

    def register(
        self,
        *,
        full_name: str,
        organization_name: str,
        email: str,
        password: str,
        locale: str,
        default_sender_email: str,
        default_sender_name: str,
    ) -> RegistrationResult:
        normalized_name = (
            self._normalize_name(
                full_name,
                maximum_length=120,
            )
        )

        normalized_organization_name = (
            self._normalize_name(
                organization_name,
                maximum_length=160,
            )
        )

        normalized_email = (
            self._normalize_email(
                email
            )
        )

        normalized_locale = (
            self._normalize_locale(
                locale
            )
        )

        clean_sender_email = (
            str(
                default_sender_email
                or ""
            ).strip()
        )

        clean_sender_name = (
            str(
                default_sender_name
                or ""
            ).strip()
        )

        try:
            self._password_service.validate_strength(
                password
            )

        except ValueError as exc:
            raise AuthServiceError(
                str(exc)
            ) from exc

        try:
            existing_user = (
                self._user_repository.get_by_email(
                    normalized_email
                )
            )

            if existing_user is not None:
                raise AuthServiceError(
                    "email_already_registered"
                )

            # ---------------------------
            # User
            # ---------------------------

            user = User(
                full_name=normalized_name,
                email=normalized_email,
                password_hash=(
                    self._password_service.hash(
                        password
                    )
                ),
                locale=normalized_locale,
                is_active=True,
            )

            self._user_repository.add(
                user
            )

            # Required before using user.id.
            db.session.flush()

            # ---------------------------
            # Organization
            # ---------------------------

            organization = Organization(
                name=(
                    normalized_organization_name
                ),
                slug=self._create_unique_slug(
                    normalized_organization_name,
                    maximum_length=160,
                    fallback="organisation",
                ),
            )

            self._organization_repository.add(
                organization
            )

            # Required before using
            # organization.id.
            db.session.flush()

            # ---------------------------
            # Organization membership
            # ---------------------------

            membership = OrganizationMember(
                organization_id=(
                    organization.id
                ),
                user_id=user.id,
                role="owner",
            )

            self._organization_repository.add_member(
                membership
            )

            # ---------------------------
            # Default project
            # ---------------------------

            project = Project(
                organization_id=(
                    organization.id
                ),
                name=DEFAULT_PROJECT_NAME,
                slug=DEFAULT_PROJECT_SLUG,
                environment="production",
                default_sender_email=(
                    clean_sender_email
                ),
                default_sender_name=(
                    clean_sender_name
                ),
            )

            self._project_repository.add(
                project
            )

            # Detect database constraints before
            # committing the transaction.
            db.session.flush()
            db.session.commit()

        except AuthServiceError:
            db.session.rollback()
            raise

        except IntegrityError as exc:
            db.session.rollback()

            raise AuthServiceError(
                "registration_conflict"
            ) from exc

        except Exception:
            db.session.rollback()
            raise

        return RegistrationResult(
            user=user,
            organization=organization,
            project=project,
        )

    # ---------------------------
    # Password authentication
    # ---------------------------

    def authenticate(
        self,
        *,
        email: str,
        password: str,
    ) -> User | None:
        try:
            normalized_email = (
                self._normalize_email(
                    email
                )
            )

        except AuthServiceError:
            self._password_service.verify_dummy(
                password
            )

            return None

        user = (
            self._user_repository.get_by_email(
                normalized_email
            )
        )

        if user is None:
            self._password_service.verify_dummy(
                password
            )

            return None

        if not user.is_active:
            self._password_service.verify_dummy(
                password
            )

            return None

        password_hash = str(
            user.password_hash
            or ""
        )

        if not password_hash:
            self._password_service.verify_dummy(
                password
            )

            return None

        password_is_valid = (
            self._password_service.verify(
                password_hash=password_hash,
                password=password,
            )
        )

        if not password_is_valid:
            return None

        if self._password_service.needs_rehash(
            password_hash
        ):
            try:
                user.password_hash = (
                    self._password_service.hash(
                        password
                    )
                )

                db.session.commit()

            except Exception:
                db.session.rollback()
                raise

        return user

    # ---------------------------
    # Email normalization
    # ---------------------------

    @staticmethod
    def _normalize_email(
        email: str,
    ) -> str:
        if not isinstance(
            email,
            str,
        ):
            raise AuthServiceError(
                "invalid_email"
            )

        clean_email = email.strip()

        if not clean_email:
            raise AuthServiceError(
                "invalid_email"
            )

        try:
            validated_email = validate_email(
                clean_email,
                check_deliverability=False,
            )

        except EmailNotValidError as exc:
            raise AuthServiceError(
                "invalid_email"
            ) from exc

        normalized_email = (
            validated_email.normalized
            .strip()
            .lower()
        )

        if len(normalized_email) > 320:
            raise AuthServiceError(
                "invalid_email"
            )

        return normalized_email

    # ---------------------------
    # Name normalization
    # ---------------------------

    @staticmethod
    def _normalize_name(
        value: str,
        *,
        maximum_length: int,
    ) -> str:
        if not isinstance(
            value,
            str,
        ):
            raise AuthServiceError(
                "invalid_name"
            )

        normalized_value = " ".join(
            value.strip().split()
        )

        if len(normalized_value) < 2:
            raise AuthServiceError(
                "invalid_name"
            )

        if len(normalized_value) > maximum_length:
            raise AuthServiceError(
                "name_too_long"
            )

        return normalized_value

    # ---------------------------
    # Locale normalization
    # ---------------------------

    @staticmethod
    def _normalize_locale(
        locale: str,
    ) -> str:
        normalized_locale = str(
            locale
            or ""
        ).strip().lower()

        normalized_locale = (
            normalized_locale
            .replace("_", "-")
            .split(
                "-",
                maxsplit=1,
            )[0]
        )

        if (
            normalized_locale
            not in SUPPORTED_LOCALES
        ):
            return DEFAULT_LOCALE

        return normalized_locale

    # ---------------------------
    # Slug generation
    # ---------------------------

    @staticmethod
    def _create_unique_slug(
        value: str,
        *,
        maximum_length: int = 160,
        fallback: str = "organisation",
    ) -> str:
        ascii_value = (
            unicodedata.normalize(
                "NFKD",
                value,
            )
            .encode(
                "ascii",
                "ignore",
            )
            .decode(
                "ascii"
            )
        )

        base_slug = re.sub(
            r"[^a-zA-Z0-9]+",
            "-",
            ascii_value.lower(),
        ).strip("-")

        if not base_slug:
            base_slug = fallback

        suffix = secrets.token_hex(4)

        available_base_length = max(
            1,
            maximum_length
            - len(suffix)
            - 1,
        )

        shortened_base_slug = (
            base_slug[
                :available_base_length
            ].rstrip("-")
        )

        if not shortened_base_slug:
            shortened_base_slug = (
                fallback[
                    :available_base_length
                ]
            )

        return (
            f"{shortened_base_slug}-{suffix}"
        )