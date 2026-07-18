from __future__ import annotations

import uuid
from dataclasses import dataclass

from email_validator import (
    EmailNotValidError,
    validate_email,
)
from sqlalchemy.exc import IntegrityError

from extensions import db
from models.api_key import ApiKey
from models.email_job import EmailJob
from models.project import Project
from repositories.email_repository import EmailRepository


class EmailQueueError(Exception):
    def __init__(
        self,
        code: str,
    ) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class QueueResult:
    email_job: EmailJob
    created: bool


class EmailQueueService:
    def __init__(
        self,
        *,
        repository: EmailRepository,
        max_attempts: int,
        subject_max_length: int,
        text_max_length: int,
        html_max_length: int,
    ) -> None:
        self._repository = repository
        self._max_attempts = max_attempts
        self._subject_max_length = subject_max_length
        self._text_max_length = text_max_length
        self._html_max_length = html_max_length

    def enqueue(
        self,
        *,
        project: Project,
        api_key: ApiKey,
        idempotency_key: str,
        payload: dict[str, object],
    ) -> QueueResult:
        normalized_idempotency_key = (
            idempotency_key.strip()
        )

        if not normalized_idempotency_key:
            raise EmailQueueError(
                "missing_idempotency_key"
            )

        if len(normalized_idempotency_key) > 200:
            raise EmailQueueError(
                "invalid_idempotency_key"
            )

        existing_job = (
            self._repository.get_by_idempotency_key(
                project_id=project.id,
                idempotency_key=normalized_idempotency_key,
            )
        )

        if existing_job is not None:
            return QueueResult(
                email_job=existing_job,
                created=False,
            )

        recipient = payload.get("to")

        if not isinstance(recipient, dict):
            raise EmailQueueError(
                "invalid_recipient"
            )

        recipient_email = self._normalize_email(
            recipient.get("email")
        )

        recipient_name = self._normalize_optional_name(
            recipient.get("name")
        )

        sender_data = payload.get("from")

        if sender_data is not None and not isinstance(
            sender_data,
            dict,
        ):
            raise EmailQueueError(
                "invalid_sender"
            )

        sender_data = (
            sender_data
            if isinstance(sender_data, dict)
            else {}
        )

        sender_email = self._normalize_email(
            sender_data.get("email")
            or project.default_sender_email
        )

        sender_name = self._normalize_required_name(
            sender_data.get("name")
            or project.default_sender_name
        )

        subject = payload.get("subject")

        if not isinstance(subject, str):
            raise EmailQueueError(
                "invalid_subject"
            )

        normalized_subject = subject.strip()

        if (
            not normalized_subject
            or len(normalized_subject)
            > self._subject_max_length
        ):
            raise EmailQueueError(
                "invalid_subject"
            )

        text_body = payload.get("text")
        html_body = payload.get("html")

        if text_body is not None and not isinstance(
            text_body,
            str,
        ):
            raise EmailQueueError(
                "invalid_text_body"
            )

        if html_body is not None and not isinstance(
            html_body,
            str,
        ):
            raise EmailQueueError(
                "invalid_html_body"
            )

        if not text_body and not html_body:
            raise EmailQueueError(
                "missing_email_content"
            )

        if (
            isinstance(text_body, str)
            and len(text_body) > self._text_max_length
        ):
            raise EmailQueueError(
                "text_body_too_large"
            )

        if (
            isinstance(html_body, str)
            and len(html_body) > self._html_max_length
        ):
            raise EmailQueueError(
                "html_body_too_large"
            )

        headers = self._normalize_headers(
            payload.get("headers")
        )

        email_job = EmailJob(
            project_id=project.id,
            api_key_id=api_key.id,
            idempotency_key=normalized_idempotency_key,
            sender_email=sender_email,
            sender_name=sender_name,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=normalized_subject,
            text_body=text_body,
            html_body=html_body,
            custom_headers=headers,
            status=EmailJob.STATUS_QUEUED,
            max_attempts=self._max_attempts,
        )

        try:
            self._repository.add(
                email_job
            )
            db.session.commit()

        except IntegrityError:
            db.session.rollback()

            existing_job = (
                self._repository.get_by_idempotency_key(
                    project_id=project.id,
                    idempotency_key=normalized_idempotency_key,
                )
            )

            if existing_job is None:
                raise

            return QueueResult(
                email_job=existing_job,
                created=False,
            )

        except Exception:
            db.session.rollback()
            raise

        return QueueResult(
            email_job=email_job,
            created=True,
        )

    @staticmethod
    def _normalize_email(
        value: object,
    ) -> str:
        if not isinstance(value, str):
            raise EmailQueueError(
                "invalid_email_address"
            )

        try:
            validated = validate_email(
                value.strip(),
                check_deliverability=False,
            )
        except EmailNotValidError as exc:
            raise EmailQueueError(
                "invalid_email_address"
            ) from exc

        return validated.normalized.lower()

    @staticmethod
    def _normalize_required_name(
        value: object,
    ) -> str:
        if not isinstance(value, str):
            raise EmailQueueError(
                "invalid_name"
            )

        normalized = " ".join(
            value.strip().split()
        )

        if not normalized or len(normalized) > 160:
            raise EmailQueueError(
                "invalid_name"
            )

        return normalized

    @staticmethod
    def _normalize_optional_name(
        value: object,
    ) -> str | None:
        if value is None:
            return None

        return EmailQueueService._normalize_required_name(
            value
        )

    @staticmethod
    def _normalize_headers(
        value: object,
    ) -> dict[str, str]:
        if value is None:
            return {}

        if not isinstance(value, dict):
            raise EmailQueueError(
                "invalid_headers"
            )

        normalized_headers: dict[str, str] = {}

        for name, header_value in value.items():
            if not isinstance(name, str):
                raise EmailQueueError(
                    "invalid_headers"
                )

            if not isinstance(header_value, str):
                raise EmailQueueError(
                    "invalid_headers"
                )

            normalized_name = name.strip()
            normalized_value = header_value.strip()

            if not normalized_name.lower().startswith("x-"):
                raise EmailQueueError(
                    "invalid_headers"
                )

            if (
                "\r" in normalized_value
                or "\n" in normalized_value
            ):
                raise EmailQueueError(
                    "invalid_headers"
                )

            normalized_headers[
                normalized_name[:100]
            ] = normalized_value[:500]

        return normalized_headers