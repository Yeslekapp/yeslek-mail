from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from extensions import db
from models.api_key import ApiKey
from repositories.api_key_repository import ApiKeyRepository


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class CreatedApiKey:
    api_key: ApiKey
    raw_key: str


class ApiKeyService:
    def __init__(
        self,
        *,
        repository: ApiKeyRepository,
        pepper: str,
        live_prefix: str,
    ) -> None:
        if len(pepper) < 16:
            raise RuntimeError(
                "API_KEY_PEPPER doit contenir au moins 16 caractères."
            )

        self._repository = repository
        self._pepper = pepper.encode("utf-8")
        self._live_prefix = live_prefix

    def create(
        self,
        *,
        project_id: uuid.UUID,
        name: str,
        scopes: list[str] | None = None,
    ) -> CreatedApiKey:
        normalized_name = " ".join(name.strip().split())

        if len(normalized_name) < 2:
            raise ValueError("invalid_api_key_name")

        raw_key = (
            self._live_prefix
            + secrets.token_urlsafe(36)
        )

        lookup_prefix = raw_key[:24]

        api_key = ApiKey(
            project_id=project_id,
            name=normalized_name,
            prefix=lookup_prefix,
            last_four=raw_key[-4:],
            key_hash=self._hash(raw_key),
            scopes=scopes or ["email:send"],
            is_active=True,
        )

        try:
            self._repository.add(api_key)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return CreatedApiKey(
            api_key=api_key,
            raw_key=raw_key,
        )

    def authenticate(
        self,
        raw_key: str,
    ) -> ApiKey | None:
        normalized_key = raw_key.strip()

        if len(normalized_key) < 30:
            return None

        lookup_prefix = normalized_key[:24]

        api_key = self._repository.get_by_prefix(
            lookup_prefix
        )

        if api_key is None:
            self._dummy_compare(normalized_key)
            return None

        if not api_key.is_active:
            return None

        if api_key.revoked_at is not None:
            return None

        if api_key.is_expired:
            return None

        calculated_hash = self._hash(
            normalized_key
        )

        if not hmac.compare_digest(
            api_key.key_hash,
            calculated_hash,
        ):
            return None

        api_key.last_used_at = utc_now()

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

        return api_key

    def revoke(
        self,
        api_key: ApiKey,
    ) -> None:
        api_key.is_active = False
        api_key.revoked_at = utc_now()

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    def _hash(
        self,
        raw_key: str,
    ) -> str:
        return hmac.new(
            self._pepper,
            raw_key.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _dummy_compare(
        self,
        raw_key: str,
    ) -> None:
        hmac.compare_digest(
            self._hash(raw_key),
            self._hash("invalid-key-placeholder"),
        )