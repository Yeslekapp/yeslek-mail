from __future__ import annotations

import uuid

from sqlalchemy import select

from extensions import db
from models.sending_domain import SendingDomain


class DomainRepository:
    def add(
        self,
        sending_domain: SendingDomain,
    ) -> SendingDomain:
        db.session.add(sending_domain)
        db.session.flush()

        return sending_domain

    def get_all(
        self,
        project_id: uuid.UUID,
    ) -> list[SendingDomain]:
        return list(
            db.session.execute(
                select(SendingDomain)
                .where(
                    SendingDomain.project_id == project_id
                )
                .order_by(
                    SendingDomain.created_at.desc()
                )
            ).scalars().all()
        )

    def get_by_id(
        self,
        *,
        domain_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> SendingDomain | None:
        return db.session.execute(
            select(SendingDomain)
            .where(
                SendingDomain.id == domain_id,
                SendingDomain.project_id == project_id,
            )
            .limit(1)
        ).scalar_one_or_none()

    def get_by_name(
        self,
        *,
        domain: str,
        project_id: uuid.UUID,
    ) -> SendingDomain | None:
        return db.session.execute(
            select(SendingDomain)
            .where(
                SendingDomain.domain == domain,
                SendingDomain.project_id == project_id,
            )
            .limit(1)
        ).scalar_one_or_none()