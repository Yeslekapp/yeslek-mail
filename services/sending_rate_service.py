from __future__ import annotations

import uuid

from extensions import db
from models.sending_rate import SendingRate
from repositories.sending_rate_repository import (
    SendingRateRepository,
)


class SendingRateService:
    def __init__(
        self,
        repository: SendingRateRepository,
    ) -> None:
        self._repository = repository

    def get_or_create(
        self,
        project_id: uuid.UUID,
    ) -> SendingRate:
        sending_rate = (
            self._repository.get_by_project(
                project_id
            )
        )

        if sending_rate is not None:
            return sending_rate

        sending_rate = SendingRate(
            project_id=project_id,
        )

        try:
            self._repository.add(
                sending_rate
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return sending_rate

    def update(
        self,
        *,
        project_id: uuid.UUID,
        emails_per_minute: int,
        emails_per_hour: int,
        emails_per_domain_per_minute: int,
        warmup_enabled: bool,
    ) -> SendingRate:
        sending_rate = self.get_or_create(
            project_id
        )

        sending_rate.emails_per_minute = (
            emails_per_minute
        )

        sending_rate.emails_per_hour = (
            emails_per_hour
        )

        sending_rate.emails_per_domain_per_minute = (
            emails_per_domain_per_minute
        )

        sending_rate.warmup_enabled = (
            warmup_enabled
        )

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return sending_rate