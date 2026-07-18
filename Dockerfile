# syntax=docker/dockerfile:1

# ---------------------------
# Python dependency builder
# ---------------------------

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN python -m venv /opt/venv

ENV PATH="/opt/venv/bin:${PATH}"

COPY requirements.txt ./requirements.txt

RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir -r requirements.txt


# ---------------------------
# Production runtime
# ---------------------------

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONHASHSEED=random

ENV PATH="/opt/venv/bin:${PATH}"

ENV PORT=8080
ENV CONTAINER_MODE=web

WORKDIR /app

RUN groupadd \
        --gid 10001 \
        yeslek \
    && useradd \
        --uid 10001 \
        --gid yeslek \
        --create-home \
        --home-dir /home/yeslek \
        --shell /usr/sbin/nologin \
        yeslek

COPY --from=builder /opt/venv /opt/venv

COPY --chown=yeslek:yeslek . /app

RUN mkdir -p \
        /app/instance \
        /app/logs \
    && chown -R yeslek:yeslek \
        /app \
        /home/yeslek

USER yeslek

EXPOSE 8080


# ---------------------------
# Web or Celery worker
# ---------------------------

CMD ["sh", "-c", "if [ \"${CONTAINER_MODE:-web}\" = \"worker\" ]; then exec celery -A celery_entry.celery_app worker --loglevel=${CELERY_LOG_LEVEL:-INFO} --concurrency=${CELERY_CONCURRENCY:-2} --queues=email-delivery,webhook-delivery,yeslek-mail --without-gossip --without-mingle; else exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers=${GUNICORN_WORKERS:-2} --threads=${GUNICORN_THREADS:-4} --timeout=${GUNICORN_TIMEOUT:-60} --graceful-timeout=${GUNICORN_GRACEFUL_TIMEOUT:-30} --keep-alive=${GUNICORN_KEEP_ALIVE:-5} --access-logfile=- --error-logfile=- --capture-output --worker-tmp-dir=/dev/shm app:app; fi"]