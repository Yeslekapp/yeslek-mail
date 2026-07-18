from __future__ import annotations

import uuid

from models.dedicated_ip import DedicatedIp
from repositories.dedicated_ip_repository import (
    DedicatedIpRepository,
)


class DedicatedIpService:
    def __init__(
        self,
        repository: DedicatedIpRepository,
    ) -> None:
        self._repository = repository

    def list_for_project(
        self,
        project_id: uuid.UUID,
    ) -> list[DedicatedIp]:
        return self._repository.get_all(
            project_id
        )