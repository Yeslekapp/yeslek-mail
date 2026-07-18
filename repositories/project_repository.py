from __future__ import annotations

import uuid

from sqlalchemy import select

from extensions import db
from models.organization_member import OrganizationMember
from models.project import Project


# ---------------------------
# Project repository
# ---------------------------

class ProjectRepository:
    def add(
        self,
        project: Project,
    ) -> Project:
        db.session.add(project)
        db.session.flush()

        return project

    def get_for_user(
        self,
        *,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Project | None:
        return db.session.execute(
            select(Project)
            .join(
                OrganizationMember,
                OrganizationMember.organization_id
                == Project.organization_id,
            )
            .where(
                Project.id == project_id,
                OrganizationMember.user_id == user_id,
            )
            .limit(1)
        ).scalar_one_or_none()

    def get_first_for_user(
        self,
        user_id: uuid.UUID,
    ) -> Project | None:
        return db.session.execute(
            select(Project)
            .join(
                OrganizationMember,
                OrganizationMember.organization_id
                == Project.organization_id,
            )
            .where(
                OrganizationMember.user_id == user_id
            )
            .order_by(
                Project.created_at.asc()
            )
            .limit(1)
        ).scalar_one_or_none()

    def get_all_for_user(
        self,
        user_id: uuid.UUID,
    ) -> list[Project]:
        return list(
            db.session.execute(
                select(Project)
                .join(
                    OrganizationMember,
                    OrganizationMember.organization_id
                    == Project.organization_id,
                )
                .where(
                    OrganizationMember.user_id == user_id
                )
                .order_by(
                    Project.name.asc()
                )
            ).scalars().all()
        )