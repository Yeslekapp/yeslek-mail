from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from extensions import db
from models.sending_domain import SendingDomain
from repositories.domain_repository import DomainRepository
from services.dns_verification_service import (
    DnsVerificationService,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DomainServiceError(Exception):
    def __init__(
        self,
        code: str,
    ) -> None:
        super().__init__(code)
        self.code = code


class DomainService:
    DOMAIN_PATTERN = re.compile(
        r"^(?!-)(?:[a-z0-9-]{1,63}\.)+[a-z]{2,63}$"
    )

    def __init__(
        self,
        *,
        repository: DomainRepository,
        dns_service: DnsVerificationService,
        dns_base_domain: str,
    ) -> None:
        self._repository = repository
        self._dns_service = dns_service
        self._dns_base_domain = (
            dns_base_domain.strip(".").lower()
        )

    def list_for_project(
        self,
        project_id: uuid.UUID,
    ) -> list[SendingDomain]:
        return self._repository.get_all(
            project_id
        )

    def create(
        self,
        *,
        project_id: uuid.UUID,
        domain: str,
    ) -> SendingDomain:
        normalized_domain = (
            domain.strip()
            .lower()
            .rstrip(".")
        )

        if not self.DOMAIN_PATTERN.fullmatch(
            normalized_domain
        ):
            raise DomainServiceError(
                "invalid_domain"
            )

        existing_domain = (
            self._repository.get_by_name(
                project_id=project_id,
                domain=normalized_domain,
            )
        )

        if existing_domain is not None:
            raise DomainServiceError(
                "domain_already_exists"
            )

        dns_records = self._build_records(
            normalized_domain
        )

        sending_domain = SendingDomain(
            project_id=project_id,
            domain=normalized_domain,
            status="pending",
            dns_records=dns_records,
            verification_results={},
        )

        try:
            self._repository.add(
                sending_domain
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return sending_domain

    def verify(
        self,
        *,
        domain_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> SendingDomain:
        sending_domain = (
            self._repository.get_by_id(
                domain_id=domain_id,
                project_id=project_id,
            )
        )

        if sending_domain is None:
            raise DomainServiceError(
                "domain_not_found"
            )

        verification_results = (
            self._dns_service.verify_records(
                sending_domain.dns_records
            )
        )

        required_keys = {
            "spf",
            "dkim",
            "return_path",
        }

        required_are_valid = all(
            verification_results.get(
                key,
                False,
            )
            for key in required_keys
        )

        sending_domain.verification_results = (
            verification_results
        )

        sending_domain.last_checked_at = utc_now()

        if required_are_valid:
            sending_domain.status = "verified"
            sending_domain.verified_at = utc_now()
        elif any(verification_results.values()):
            sending_domain.status = "partial"
            sending_domain.verified_at = None
        else:
            sending_domain.status = "pending"
            sending_domain.verified_at = None

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return sending_domain

    def _build_records(
        self,
        domain: str,
    ) -> list[dict[str, object]]:
        return [
            {
                "key": "spf",
                "label": "SPF",
                "type": "TXT",
                "host": domain,
                "value": (
                    f"v=spf1 include:spf."
                    f"{self._dns_base_domain} ~all"
                ),
                "required": True,
            },
            {
                "key": "dkim",
                "label": "DKIM",
                "type": "CNAME",
                "host": (
                    f"yeslek1._domainkey.{domain}"
                ),
                "value": (
                    f"yeslek1._domainkey."
                    f"{self._dns_base_domain}"
                ),
                "required": True,
            },
            {
                "key": "return_path",
                "label": "Return-Path",
                "type": "CNAME",
                "host": f"mail.{domain}",
                "value": (
                    f"bounce.{self._dns_base_domain}"
                ),
                "required": True,
            },
            {
                "key": "dmarc",
                "label": "DMARC",
                "type": "TXT",
                "host": f"_dmarc.{domain}",
                "value": (
                    "v=DMARC1; p=none; "
                    f"rua=mailto:dmarc@"
                    f"{self._dns_base_domain}"
                ),
                "required": False,
            },
        ]