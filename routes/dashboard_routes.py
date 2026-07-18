from __future__ import annotations

from flask import (
    Blueprint,
    current_app,
    render_template,
    request,
    session,
)
from flask_login import (
    current_user,
    login_required,
)

from repositories.email_repository import EmailRepository
from repositories.project_repository import (
    ProjectRepository,
)
from services.dashboard_service import DashboardService


dashboard_bp = Blueprint(
    "dashboard",
    __name__,
    url_prefix="/dashboard",
)


# ---------------------------
# Dashboard service factory
# ---------------------------

def create_dashboard_service() -> DashboardService:
    return DashboardService(
        project_repository=ProjectRepository(),
        email_repository=EmailRepository(),
    )


# ---------------------------
# Dashboard homepage
# ---------------------------

@dashboard_bp.get("/")
@login_required
def index():
    requested_project_id = (
        request.args.get(
            "project"
        )
        or session.get(
            "active_project_id"
        )
    )

    dashboard_service = (
        create_dashboard_service()
    )

    dashboard_data = dashboard_service.build(
        user_id=current_user.id,
        requested_project_id=(
            requested_project_id
        ),
        monthly_email_limit=int(
            current_app.config.get(
                "DEFAULT_MONTHLY_EMAIL_LIMIT",
                300,
            )
        ),
    )

    if dashboard_data.project is not None:
        session[
            "active_project_id"
        ] = str(
            dashboard_data.project.id
        )

    return render_template(
        "dashboard/index.html",
        project=dashboard_data.project,
        projects=dashboard_data.projects,
        stats=dashboard_data.stats,
        email_limit=dashboard_data.email_limit,
        email_used=dashboard_data.email_used,
        recent_emails=dashboard_data.recent_emails,
    )