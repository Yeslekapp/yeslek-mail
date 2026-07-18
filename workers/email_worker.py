from __future__ import annotations

import uuid
from datetime import datetime, timezone

from celery import shared_task
from flask import current_app

from extensions import db
from models.email_job import EmailJob
from services.email.smtp_submitter import (
    SmtpConfiguration,
    SmtpSubmitter,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_smtp_submitter() -> SmtpSubmitter:
    return SmtpSubmitter(
        SmtpConfiguration(
            host=current_app.config[
                "SMTP_HOST"
            ],
            port=current_app.config[
                "SMTP_PORT"
            ],
            username=current_app.config[
                "SMTP_USERNAME"
            ],
            password=current_app.config[
                "SMTP_PASSWORD"
            ],
            use_tls=current_app.config[
                "SMTP_USE_TLS"
            ],
            use_ssl=current_app.config[
                "SMTP_USE_SSL"
            ],
            timeout_seconds=current_app.config[
                "SMTP_TIMEOUT_SECONDS"
            ],
            message_id_domain=current_app.config[
                "MAIL_MESSAGE_ID_DOMAIN"
            ],
        )
    )


@shared_task(
    bind=True,
    name="workers.email_worker.deliver_email",
    max_retries=20,
)
def deliver_email(
    self,
    email_job_id: str,
) -> dict[str, object]:
    try:
        parsed_email_job_id = uuid.UUID(
            email_job_id
        )
    except ValueError:
        return {
            "status": "invalid_id",
        }

    email_job = db.session.get(
        EmailJob,
        parsed_email_job_id,
    )

    if email_job is None:
        return {
            "status": "not_found",
        }

    if email_job.status == EmailJob.STATUS_SENT:
        return {
            "status": "already_sent",
            "message_id": email_job.message_id,
        }

    if email_job.attempts >= email_job.max_attempts:
        email_job.status = EmailJob.STATUS_FAILED
        email_job.failed_at = utc_now()

        db.session.commit()

        return {
            "status": "failed",
            "reason": "maximum_attempts_reached",
        }

    email_job.status = EmailJob.STATUS_PROCESSING
    email_job.attempts += 1
    email_job.last_error = None

    db.session.commit()

    try:
        message_id = create_smtp_submitter().submit(
            email_job
        )

    except Exception as exc:
        db.session.rollback()

        email_job = db.session.get(
            EmailJob,
            parsed_email_job_id,
        )

        if email_job is None:
            raise

        email_job.last_error = str(exc)[:2000]

        if email_job.attempts < email_job.max_attempts:
            email_job.status = EmailJob.STATUS_DEFERRED

            db.session.commit()

            countdown = min(
                60 * (2 ** max(
                    email_job.attempts - 1,
                    0,
                )),
                3600,
            )

            raise self.retry(
                exc=exc,
                countdown=countdown,
            )

        email_job.status = EmailJob.STATUS_FAILED
        email_job.failed_at = utc_now()

        db.session.commit()

        return {
            "status": "failed",
            "error": email_job.last_error,
        }

    email_job.status = EmailJob.STATUS_SENT
    email_job.message_id = message_id
    email_job.sent_at = utc_now()
    email_job.last_error = None

    db.session.commit()

    return {
        "status": "sent",
        "message_id": message_id,
    }