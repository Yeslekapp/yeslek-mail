from __future__ import annotations

from celery import shared_task
from flask import current_app


@shared_task(
    name="workers.webhook_worker.dispatch_webhook"
)
def dispatch_webhook(
    event_name: str,
    payload: dict[str, object],
) -> dict[str, object]:
    current_app.logger.info(
        "Webhook event prepared: %s",
        event_name,
    )

    return {
        "status": "not_configured",
        "event": event_name,
        "payload": payload,
    }