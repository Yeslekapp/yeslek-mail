from __future__ import annotations

import uuid
from datetime import datetime, timezone

from email_validator import (
    EmailNotValidError,
    validate_email,
)

from extensions import db
from models.sender import Sender
from repositories.domain_repository import DomainRepository
from repositories.sender_repository import SenderRepository


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SenderServiceError(Exception):
    def __init__(
        self,
        code: str,
    ) -> None:
        super().__init__(code)
        self.code = code


class SenderService:
    def __init__(
        self,
        *,
        sender_repository: SenderRepository,
        domain_repository: DomainRepository,
    ) -> None:
        self._sender_repository = sender_repository
        self._domain_repository = domain_repository

    def list_for_project(
        self,
        project_id: uuid.UUID,
    ) -> list[Sender]:
        return self._sender_repository.get_all(
            project_id
        )

    def create(
        self,
        *,
        project_id: uuid.UUID,
        name: str,
        email: str,
    ) -> Sender:
        normalized_name = " ".join(
            name.strip().split()
        )

        if len(normalized_name) < 2:
            raise SenderServiceError(
                "invalid_sender_name"
            )

        try:
            validated_email = validate_email(
                email.strip(),
                check_deliverability=False,
            )
        except EmailNotValidError as exc:
            raise SenderServiceError(
                "invalid_sender_email"
            ) from exc

        normalized_email = (
            validated_email.normalized.lower()
        )

        existing_sender = (
            self._sender_repository.get_by_email(
                project_id=project_id,
                email=normalized_email,
            )
        )

        if existing_sender is not None:
            raise SenderServiceError(
                "sender_already_exists"
            )

        domain_name = normalized_email.rsplit(
            "@",
            1,
        )[1]

        sending_domain = (
            self._domain_repository.get_by_name(
                project_id=project_id,
                domain=domain_name,
            )
        )

        is_verified = (
            sending_domain is not None
            and sending_domain.status == "verified"
        )

        sender = Sender(
            project_id=project_id,
            name=normalized_name,
            email=normalized_email,
            domain=domain_name,
            status=(
                "verified"
                if is_verified
                else "pending"
            ),
            verified_at=(
                utc_now()
                if is_verified
                else None
            ),
        )

        try:
            self._sender_repository.add(sender)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return sender

    def update(
        self,
        *,
        sender_id: uuid.UUID,
        project_id: uuid.UUID,
        name: str,
        email: str,
    ) -> Sender:
        sender = self._sender_repository.get_by_id(
            sender_id=sender_id,
            project_id=project_id,
        )

        if sender is None:
            raise SenderServiceError(
                "sender_not_found"
            )

        normalized_name = " ".join(
            name.strip().split()
        )

        try:
            normalized_email = validate_email(
                email.strip(),
                check_deliverability=False,
            ).normalized.lower()
        except EmailNotValidError as exc:
            raise SenderServiceError(
                "invalid_sender_email"
            ) from exc

        sender.name = normalized_name
        sender.email = normalized_email
        sender.domain = normalized_email.rsplit(
            "@",
            1,
        )[1]

        sending_domain = (
            self._domain_repository.get_by_name(
                project_id=project_id,
                domain=sender.domain,
            )
        )

        if (
            sending_domain is not None
            and sending_domain.status == "verified"
        ):
            sender.status = "verified"
            sender.verified_at = utc_now()
        else:
            sender.status = "pending"
            sender.verified_at = None

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return sender

    def delete(
        self,
        *,
        sender_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> None:
        sender = self._sender_repository.get_by_id(
            sender_id=sender_id,
            project_id=project_id,
        )

        if sender is None:
            raise SenderServiceError(
                "sender_not_found"
            )

        try:
            self._sender_repository.delete(sender)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise