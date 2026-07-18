from __future__ import annotations

import uuid

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import (
    current_user,
    login_required,
)

from forms.domain_forms import DomainForm
from forms.sender_forms import SenderForm
from forms.sending_rate_forms import SendingRateForm
from repositories.dedicated_ip_repository import (
    DedicatedIpRepository,
)
from repositories.domain_repository import (
    DomainRepository,
)
from repositories.project_repository import (
    ProjectRepository,
)
from repositories.sender_repository import (
    SenderRepository,
)
from repositories.sending_rate_repository import (
    SendingRateRepository,
)
from services.dedicated_ip_service import (
    DedicatedIpService,
)
from services.dns_verification_service import (
    DnsVerificationService,
)
from services.domain_service import (
    DomainService,
    DomainServiceError,
)
from services.project_service import ProjectService
from services.sender_service import (
    SenderService,
    SenderServiceError,
)
from services.sending_rate_service import (
    SendingRateService,
)


settings_bp = Blueprint(
    "settings",
    __name__,
    url_prefix="/settings",
)


def get_current_project():
    project = ProjectService(
        ProjectRepository()
    ).get_active_project(
        user_id=current_user.id,
        requested_project_id=session.get(
            "active_project_id"
        ),
    )

    if project is None:
        abort(404)

    session["active_project_id"] = str(
        project.id
    )

    return project


def create_sender_service() -> SenderService:
    return SenderService(
        sender_repository=SenderRepository(),
        domain_repository=DomainRepository(),
    )


def create_domain_service() -> DomainService:
    return DomainService(
        repository=DomainRepository(),
        dns_service=DnsVerificationService(),
        dns_base_domain=current_app.config.get(
            "MAIL_DNS_BASE_DOMAIN",
            current_app.config[
                "MAIL_MESSAGE_ID_DOMAIN"
            ],
        ),
    )


@settings_bp.get("/senders-domains")
@login_required
def senders_domains():
    project = get_current_project()

    active_tab = request.args.get(
        "tab",
        "senders",
    )

    allowed_tabs = {
        "senders",
        "domains",
        "dedicated-ips",
        "sending-rate",
    }

    if active_tab not in allowed_tabs:
        active_tab = "senders"

    senders = create_sender_service().list_for_project(
        project.id
    )

    domains = create_domain_service().list_for_project(
        project.id
    )

    dedicated_ips = DedicatedIpService(
        DedicatedIpRepository()
    ).list_for_project(
        project.id
    )

    sending_rate = SendingRateService(
        SendingRateRepository()
    ).get_or_create(
        project.id
    )

    return render_template(
        "settings/senders_domains.html",
        project=project,
        active_tab=active_tab,
        senders=senders,
        domains=domains,
        dedicated_ips=dedicated_ips,
        sending_rate=sending_rate,
    )


@settings_bp.route(
    "/senders/new",
    methods=["GET", "POST"],
)
@login_required
def sender_create():
    project = get_current_project()
    form = SenderForm()

    if form.validate_on_submit():
        try:
            create_sender_service().create(
                project_id=project.id,
                name=form.name.data,
                email=form.email.data,
            )
        except SenderServiceError as exc:
            flash(
                exc.code,
                "danger",
            )
        else:
            flash(
                "Expéditeur ajouté.",
                "success",
            )

            return redirect(
                url_for(
                    "settings.senders_domains",
                    tab="senders",
                )
            )

    return render_template(
        "settings/sender_create.html",
        form=form,
        project=project,
    )


@settings_bp.route(
    "/senders/<uuid:sender_id>/edit",
    methods=["GET", "POST"],
)
@login_required
def sender_edit(sender_id: uuid.UUID):
    project = get_current_project()

    sender = SenderRepository().get_by_id(
        sender_id=sender_id,
        project_id=project.id,
    )

    if sender is None:
        abort(404)

    form = SenderForm(
        obj=sender
    )

    if form.validate_on_submit():
        try:
            create_sender_service().update(
                sender_id=sender.id,
                project_id=project.id,
                name=form.name.data,
                email=form.email.data,
            )
        except SenderServiceError as exc:
            flash(
                exc.code,
                "danger",
            )
        else:
            flash(
                "Expéditeur modifié.",
                "success",
            )

            return redirect(
                url_for(
                    "settings.senders_domains",
                    tab="senders",
                )
            )

    return render_template(
        "settings/sender_edit.html",
        form=form,
        sender=sender,
        project=project,
    )


@settings_bp.post(
    "/senders/<uuid:sender_id>/delete"
)
@login_required
def sender_delete(sender_id: uuid.UUID):
    project = get_current_project()

    try:
        create_sender_service().delete(
            sender_id=sender_id,
            project_id=project.id,
        )
    except SenderServiceError:
        abort(404)

    flash(
        "Expéditeur supprimé.",
        "success",
    )

    return redirect(
        url_for(
            "settings.senders_domains",
            tab="senders",
        )
    )


@settings_bp.route(
    "/domains/new",
    methods=["GET", "POST"],
)
@login_required
def domain_create():
    project = get_current_project()
    form = DomainForm()

    if form.validate_on_submit():
        try:
            sending_domain = (
                create_domain_service().create(
                    project_id=project.id,
                    domain=form.domain.data,
                )
            )
        except DomainServiceError as exc:
            flash(
                exc.code,
                "danger",
            )
        else:
            return redirect(
                url_for(
                    "settings.domain_detail",
                    domain_id=sending_domain.id,
                )
            )

    return render_template(
        "settings/domain_create.html",
        form=form,
        project=project,
    )


@settings_bp.get(
    "/domains/<uuid:domain_id>"
)
@login_required
def domain_detail(domain_id: uuid.UUID):
    project = get_current_project()

    sending_domain = (
        DomainRepository().get_by_id(
            domain_id=domain_id,
            project_id=project.id,
        )
    )

    if sending_domain is None:
        abort(404)

    return render_template(
        "settings/domain_detail.html",
        project=project,
        sending_domain=sending_domain,
    )


@settings_bp.post(
    "/domains/<uuid:domain_id>/verify"
)
@login_required
def domain_verify(domain_id: uuid.UUID):
    project = get_current_project()

    try:
        sending_domain = (
            create_domain_service().verify(
                domain_id=domain_id,
                project_id=project.id,
            )
        )
    except DomainServiceError:
        abort(404)

    flash(
        (
            "Domaine vérifié."
            if sending_domain.status == "verified"
            else "La configuration DNS est encore incomplète."
        ),
        (
            "success"
            if sending_domain.status == "verified"
            else "warning"
        ),
    )

    return redirect(
        url_for(
            "settings.domain_detail",
            domain_id=domain_id,
        )
    )


@settings_bp.route(
    "/sending-rate",
    methods=["GET", "POST"],
)
@login_required
def sending_rate():
    project = get_current_project()

    service = SendingRateService(
        SendingRateRepository()
    )

    current_rate = service.get_or_create(
        project.id
    )

    form = SendingRateForm(
        obj=current_rate
    )

    if form.validate_on_submit():
        service.update(
            project_id=project.id,
            emails_per_minute=(
                form.emails_per_minute.data
            ),
            emails_per_hour=(
                form.emails_per_hour.data
            ),
            emails_per_domain_per_minute=(
                form.emails_per_domain_per_minute.data
            ),
            warmup_enabled=(
                form.warmup_enabled.data
            ),
        )

        flash(
            "Cadence d’envoi enregistrée.",
            "success",
        )

        return redirect(
            url_for(
                "settings.senders_domains",
                tab="sending-rate",
            )
        )

    return render_template(
        "settings/sending_rate.html",
        project=project,
        form=form,
    )