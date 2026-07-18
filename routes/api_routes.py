from __future__ import annotations

from functools import wraps
from typing import Callable, TypeVar

from flask import (
    Blueprint,
    current_app,
    g,
    jsonify,
    request,
)

from extensions import csrf, limiter
from repositories.api_key_repository import (
    ApiKeyRepository,
)
from repositories.email_repository import (
    EmailRepository,
)
from services.email.queue_service import (
    EmailQueueError,
    EmailQueueService,
)
from services.security.api_key_service import (
    ApiKeyService,
)
from workers.email_worker import deliver_email


api_bp = Blueprint(
    "api",
    __name__,
    url_prefix="/api/v1",
)

ViewFunction = TypeVar(
    "ViewFunction",
    bound=Callable,
)


def create_api_key_service() -> ApiKeyService:
    return ApiKeyService(
        repository=ApiKeyRepository(),
        pepper=current_app.config[
            "API_KEY_PEPPER"
        ],
        live_prefix=current_app.config[
            "API_KEY_PREFIX"
        ],
    )


def require_api_key(
    view_function: ViewFunction,
) -> ViewFunction:
    @wraps(view_function)
    def wrapped(*args, **kwargs):
        authorization = request.headers.get(
            "Authorization",
            "",
        )

        scheme, separator, raw_key = (
            authorization.partition(" ")
        )

        if (
            separator != " "
            or scheme.lower() != "bearer"
            or not raw_key.strip()
        ):
            return jsonify(
                {
                    "error": {
                        "code": "invalid_api_key",
                        "message": (
                            "Une clé API Bearer valide "
                            "est obligatoire."
                        ),
                    }
                }
            ), 401

        api_key = (
            create_api_key_service().authenticate(
                raw_key
            )
        )

        if api_key is None:
            return jsonify(
                {
                    "error": {
                        "code": "invalid_api_key",
                        "message": (
                            "La clé API est invalide, "
                            "expirée ou révoquée."
                        ),
                    }
                }
            ), 401

        if "email:send" not in api_key.scopes:
            return jsonify(
                {
                    "error": {
                        "code": "missing_scope",
                        "message": (
                            "La clé API ne possède pas "
                            "la permission email:send."
                        ),
                    }
                }
            ), 403

        g.api_key = api_key
        g.project = api_key.project

        return view_function(
            *args,
            **kwargs,
        )

    return wrapped  # type: ignore[return-value]


@api_bp.post("/emails/send")
@csrf.exempt
@limiter.limit(
    lambda: current_app.config[
        "API_EMAIL_SEND_RATE_LIMIT"
    ]
)
@require_api_key
def send_email():
    payload = request.get_json(
        silent=True
    )

    if not isinstance(payload, dict):
        return jsonify(
            {
                "error": {
                    "code": "invalid_json",
                    "message": (
                        "Le corps doit contenir "
                        "un objet JSON valide."
                    ),
                }
            }
        ), 400

    idempotency_key = request.headers.get(
        "Idempotency-Key",
        "",
    )

    queue_service = EmailQueueService(
        repository=EmailRepository(),
        max_attempts=current_app.config[
            "EMAIL_MAX_ATTEMPTS"
        ],
        subject_max_length=current_app.config[
            "EMAIL_SUBJECT_MAX_LENGTH"
        ],
        text_max_length=current_app.config[
            "EMAIL_TEXT_MAX_LENGTH"
        ],
        html_max_length=current_app.config[
            "EMAIL_HTML_MAX_LENGTH"
        ],
    )

    try:
        result = queue_service.enqueue(
            project=g.project,
            api_key=g.api_key,
            idempotency_key=idempotency_key,
            payload=payload,
        )

    except EmailQueueError as exc:
        return jsonify(
            {
                "error": {
                    "code": exc.code,
                    "message": (
                        "Les données de l’e-mail "
                        "sont invalides."
                    ),
                }
            }
        ), 400

    if result.created:
        deliver_email.delay(
            str(result.email_job.id)
        )

    return jsonify(
        {
            "id": str(
                result.email_job.id
            ),
            "status": result.email_job.status,
            "created": result.created,
            "idempotency_key": (
                result.email_job.idempotency_key
            ),
        }
    ), (
        202
        if result.created
        else 200
    )


@api_bp.get("/emails/<uuid:email_job_id>")
@csrf.exempt
@limiter.limit("120 per minute")
@require_api_key
def get_email(
    email_job_id,
):
    email_job = EmailRepository().get_by_id(
        email_job_id
    )

    if (
        email_job is None
        or email_job.project_id
        != g.project.id
    ):
        return jsonify(
            {
                "error": {
                    "code": "email_not_found",
                    "message": "E-mail introuvable.",
                }
            }
        ), 404

    return jsonify(
        {
            "id": str(email_job.id),
            "status": email_job.status,
            "recipient": email_job.recipient_email,
            "subject": email_job.subject,
            "attempts": email_job.attempts,
            "message_id": email_job.message_id,
            "created_at": (
                email_job.created_at.isoformat()
            ),
            "sent_at": (
                email_job.sent_at.isoformat()
                if email_job.sent_at
                else None
            ),
        }
    )