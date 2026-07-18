from __future__ import annotations

from celery import Celery, Task
from flask import Flask


def init_celery(
    app: Flask,
) -> Celery:
    class FlaskTask(Task):
        abstract = True

        def __call__(
            self,
            *args,
            **kwargs,
        ):
            with app.app_context():
                return self.run(
                    *args,
                    **kwargs,
                )

    celery_app = Celery(
        app.import_name,
        task_cls=FlaskTask,
    )

    celery_app.config_from_object(
        app.config["CELERY"]
    )

    celery_app.conf.update(
        imports=(
            "workers.email_worker",
            "workers.webhook_worker",
        ),
    )

    celery_app.set_default()

    app.extensions["celery"] = celery_app

    return celery_app