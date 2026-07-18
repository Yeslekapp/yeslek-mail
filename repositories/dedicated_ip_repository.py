from __future__ import annotations

import uuid

from sqlalchemy import select

from extensions import db
from models.dedicated_ip import DedicatedIp


class DedicatedIpRepository:
    def get_all(
        self,
        project_id: uuid.UUID,
    ) -> list[DedicatedIp]:
        return list(
            db.session.execute(
                select(DedicatedIp)
                .where(
                    DedicatedIp.project_id == project_id
                )
                .order_by(
                    DedicatedIp.created_at.desc()
                )
            ).scalars().all()
        )