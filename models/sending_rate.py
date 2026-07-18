from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SendingRate(db.Model):
    __tablename__ = "sending_rates"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            name="uq_sending_rate_project",
        ),
    )

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

    emails_per_minute: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60,
    )

    emails_per_hour: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1000,
    )

    emails_per_domain_per_minute: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=30,
    )

    warmup_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )