from __future__ import annotations

from typing import Any

import dns.exception
import dns.resolver


class DnsVerificationService:
    def verify_records(
        self,
        records: list[dict[str, Any]],
    ) -> dict[str, bool]:
        results: dict[str, bool] = {}

        for record in records:
            key = str(record.get("key", "unknown"))
            record_type = str(
                record.get("type", "")
            ).upper()

            host = str(record.get("host", ""))
            expected_value = str(
                record.get("value", "")
            )

            if record_type == "TXT":
                results[key] = self._verify_txt(
                    host,
                    expected_value,
                )

            elif record_type == "CNAME":
                results[key] = self._verify_cname(
                    host,
                    expected_value,
                )

            else:
                results[key] = False

        return results

    @staticmethod
    def _verify_txt(
        host: str,
        expected_value: str,
    ) -> bool:
        try:
            answers = dns.resolver.resolve(
                host,
                "TXT",
                lifetime=5,
            )
        except (
            dns.exception.DNSException,
            OSError,
        ):
            return False

        expected = expected_value.strip()

        for answer in answers:
            actual = "".join(
                part.decode("utf-8")
                for part in answer.strings
            ).strip()

            if actual == expected:
                return True

        return False

    @staticmethod
    def _verify_cname(
        host: str,
        expected_value: str,
    ) -> bool:
        try:
            answers = dns.resolver.resolve(
                host,
                "CNAME",
                lifetime=5,
            )
        except (
            dns.exception.DNSException,
            OSError,
        ):
            return False

        expected = expected_value.rstrip(".").lower()

        for answer in answers:
            actual = str(
                answer.target
            ).rstrip(".").lower()

            if actual == expected:
                return True

        return False