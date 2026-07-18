from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select

from extensions import db
from models.email_job import EmailJob


class EmailRepository:
    def add(
        self,
        email_job: EmailJob,
    ) -> EmailJob:
        db.session.add(email_job)
        db.session.flush()

        return email_job

    def get_by_id(
        self,
        email_job_id: uuid.UUID,
    ) -> EmailJob | None:
        return db.session.get(
            EmailJob,
            email_job_id,
        )

    def get_by_idempotency_key(
        self,
        *,
        project_id: uuid.UUID,
        idempotency_key: str,
    ) -> EmailJob | None:
        return db.session.execute(
            select(EmailJob)
            .where(
                EmailJob.project_id == project_id,
                EmailJob.idempotency_key == idempotency_key,
            )
            .limit(1)
        ).scalar_one_or_none()

    def count_by_status(
        self,
        *,
        project_id: uuid.UUID,
        created_after: datetime,
    ) -> dict[str, int]:
        rows = db.session.execute(
            select(
                EmailJob.status,
                func.count(EmailJob.id),
            )
            .where(
                EmailJob.project_id == project_id,
                EmailJob.created_at >= created_after,
            )
            .group_by(EmailJob.status)
        ).all()

        return {
            str(status): int(count)
            for status, count in rows
        }

    def count_created_between(
        self,
        *,
        project_id: uuid.UUID,
        created_after: datetime,
        created_before: datetime,
    ) -> int:
        value = db.session.execute(
            select(func.count(EmailJob.id))
            .where(
                EmailJob.project_id == project_id,
                EmailJob.created_at >= created_after,
                EmailJob.created_at < created_before,
            )
        ).scalar_one()

        return int(value)

    def get_recent(
        self,
        *,
        project_id: uuid.UUID,
        limit: int = 10,
    ) -> list[EmailJob]:
        safe_limit = max(
            1,
            min(limit, 100),
        )

        return list(
            db.session.execute(
                select(EmailJob)
                .where(
                    EmailJob.project_id == project_id
                )
                .order_by(
                    EmailJob.created_at.desc()
                )
                .limit(safe_limit)
            ).scalars().all()
        )