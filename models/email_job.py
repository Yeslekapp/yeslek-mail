from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EmailJob(db.Model):
    __tablename__ = "email_jobs"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_email_job_project_idempotency",
        ),
    )

    STATUS_QUEUED = "queued"
    STATUS_PROCESSING = "processing"
    STATUS_DEFERRED = "deferred"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_BOUNCED = "bounced"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "projects.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "api_keys.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    sender_email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )

    sender_name: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
    )

    recipient_email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        index=True,
    )

    recipient_name: Mapped[str | None] = mapped_column(
        String(160),
        nullable=True,
    )

    subject: Mapped[str] = mapped_column(
        String(998),
        nullable=False,
    )

    text_body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    html_body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    custom_headers: Mapped[dict[str, str]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=STATUS_QUEUED,
        index=True,
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    message_id: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
        index=True,
    )

    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    project = relationship(
        "Project",
        back_populates="email_jobs",
    )

    api_key = relationship("ApiKey")