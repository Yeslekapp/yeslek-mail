from __future__ import annotations

import uuid

from models.project import Project
from repositories.project_repository import (
    ProjectRepository,
)


# ---------------------------
# Project service
# ---------------------------

class ProjectService:
    def __init__(
        self,
        project_repository: ProjectRepository,
    ) -> None:
        self._project_repository = project_repository

    def get_active_project(
        self,
        *,
        user_id: uuid.UUID,
        requested_project_id: str | None,
    ) -> Project | None:
        parsed_project_id = self._parse_uuid(
            requested_project_id
        )

        if parsed_project_id is not None:
            requested_project = (
                self._project_repository.get_for_user(
                    project_id=parsed_project_id,
                    user_id=user_id,
                )
            )

            if requested_project is not None:
                return requested_project

        return self._project_repository.get_first_for_user(
            user_id
        )

    def get_user_projects(
        self,
        user_id: uuid.UUID,
    ) -> list[Project]:
        return self._project_repository.get_all_for_user(
            user_id
        )

    @staticmethod
    def _parse_uuid(
        value: str | None,
    ) -> uuid.UUID | None:
        if not value:
            return None

        try:
            return uuid.UUID(
                value
            )
        except ValueError:
            return None