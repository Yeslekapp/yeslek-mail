from __future__ import annotations

import uuid

from sqlalchemy import select

from extensions import db
from models.sending_rate import SendingRate


class SendingRateRepository:
    def get_by_project(
        self,
        project_id: uuid.UUID,
    ) -> SendingRate | None:
        return db.session.execute(
            select(SendingRate)
            .where(
                SendingRate.project_id == project_id
            )
            .limit(1)
        ).scalar_one_or_none()

    def add(
        self,
        sending_rate: SendingRate,
    ) -> SendingRate:
        db.session.add(sending_rate)
        db.session.flush()

        return sending_rate