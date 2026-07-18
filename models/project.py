from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Project(db.Model):
    __tablename__ = "projects"

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "slug",
            name="uq_project_organization_slug",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "organizations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(190),
        nullable=False,
    )

    environment: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="production",
    )

    default_sender_email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )

    default_sender_name: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
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

    organization = relationship(
        "Organization",
        back_populates="projects",
    )

    email_jobs = relationship(
        "EmailJob",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    api_keys = relationship(
        "ApiKey",
        back_populates="project",
        cascade="all, delete-orphan",
    )