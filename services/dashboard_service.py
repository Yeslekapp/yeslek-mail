from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from models.email_job import EmailJob
from models.project import Project
from repositories.email_repository import EmailRepository
from repositories.project_repository import (
    ProjectRepository,
)
from services.project_service import ProjectService


# ---------------------------
# Dashboard data
# ---------------------------

@dataclass(frozen=True, slots=True)
class DashboardData:
    project: Project | None
    projects: list[Project]
    stats: dict[str, int]
    email_limit: int
    email_used: int
    recent_emails: list[EmailJob]


# ---------------------------
# Dashboard service
# ---------------------------

class DashboardService:
    def __init__(
        self,
        *,
        project_repository: ProjectRepository,
        email_repository: EmailRepository,
    ) -> None:
        self._project_repository = project_repository
        self._email_repository = email_repository

        self._project_service = ProjectService(
            project_repository
        )

    def build(
        self,
        *,
        user_id: uuid.UUID,
        requested_project_id: str | None,
        monthly_email_limit: int,
    ) -> DashboardData:
        project = self._project_service.get_active_project(
            user_id=user_id,
            requested_project_id=requested_project_id,
        )

        projects = (
            self._project_service.get_user_projects(
                user_id
            )
        )

        default_stats = {
            "queued": 0,
            "processing": 0,
            "sent": 0,
            "failed": 0,
            "deferred": 0,
            "bounced": 0,
        }

        if project is None:
            return DashboardData(
                project=None,
                projects=projects,
                stats=default_stats,
                email_limit=monthly_email_limit,
                email_used=0,
                recent_emails=[],
            )

        now = datetime.now(
            timezone.utc
        )

        seven_days_ago = now - timedelta(
            days=7
        )

        month_start = datetime(
            year=now.year,
            month=now.month,
            day=1,
            tzinfo=timezone.utc,
        )

        if now.month == 12:
            next_month_start = datetime(
                year=now.year + 1,
                month=1,
                day=1,
                tzinfo=timezone.utc,
            )
        else:
            next_month_start = datetime(
                year=now.year,
                month=now.month + 1,
                day=1,
                tzinfo=timezone.utc,
            )

        stored_stats = (
            self._email_repository.count_by_status(
                project_id=project.id,
                created_after=seven_days_ago,
            )
        )

        stats = {
            **default_stats,
            **stored_stats,
        }

        email_used = (
            self._email_repository.count_created_between(
                project_id=project.id,
                created_after=month_start,
                created_before=next_month_start,
            )
        )

        recent_emails = (
            self._email_repository.get_recent(
                project_id=project.id,
                limit=10,
            )
        )

        return DashboardData(
            project=project,
            projects=projects,
            stats=stats,
            email_limit=max(
                monthly_email_limit,
                1,
            ),
            email_used=email_used,
            recent_emails=recent_emails,
        )