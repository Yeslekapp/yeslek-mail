from __future__ import annotations

import uuid

from sqlalchemy import select

from extensions import db
from models.api_key import ApiKey


class ApiKeyRepository:
    def add(self, api_key: ApiKey) -> ApiKey:
        db.session.add(api_key)
        db.session.flush()

        return api_key

    def get_by_prefix(
        self,
        prefix: str,
    ) -> ApiKey | None:
        return db.session.execute(
            select(ApiKey)
            .where(ApiKey.prefix == prefix)
            .limit(1)
        ).scalar_one_or_none()

    def get_for_project(
        self,
        *,
        api_key_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> ApiKey | None:
        return db.session.execute(
            select(ApiKey)
            .where(
                ApiKey.id == api_key_id,
                ApiKey.project_id == project_id,
            )
            .limit(1)
        ).scalar_one_or_none()