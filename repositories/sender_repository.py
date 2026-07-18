from __future__ import annotations

import uuid

from sqlalchemy import select

from extensions import db
from models.sender import Sender


class SenderRepository:
    def add(self, sender: Sender) -> Sender:
        db.session.add(sender)
        db.session.flush()

        return sender

    def get_all(
        self,
        project_id: uuid.UUID,
    ) -> list[Sender]:
        return list(
            db.session.execute(
                select(Sender)
                .where(Sender.project_id == project_id)
                .order_by(Sender.created_at.desc())
            ).scalars().all()
        )

    def get_by_id(
        self,
        *,
        sender_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> Sender | None:
        return db.session.execute(
            select(Sender)
            .where(
                Sender.id == sender_id,
                Sender.project_id == project_id,
            )
            .limit(1)
        ).scalar_one_or_none()

    def get_by_email(
        self,
        *,
        email: str,
        project_id: uuid.UUID,
    ) -> Sender | None:
        return db.session.execute(
            select(Sender)
            .where(
                Sender.email == email,
                Sender.project_id == project_id,
            )
            .limit(1)
        ).scalar_one_or_none()

    def delete(self, sender: Sender) -> None:
        db.session.delete(sender)