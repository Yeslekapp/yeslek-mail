from __future__ import annotations

import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid

from models.email_job import EmailJob


class SmtpSubmissionError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class SmtpConfiguration:
    host: str
    port: int
    username: str
    password: str
    use_tls: bool
    use_ssl: bool
    timeout_seconds: int
    message_id_domain: str


class SmtpSubmitter:
    def __init__(
        self,
        configuration: SmtpConfiguration,
    ) -> None:
        self._configuration = configuration

    def submit(
        self,
        email_job: EmailJob,
    ) -> str:
        message = self._build_message(
            email_job
        )

        try:
            if self._configuration.use_ssl:
                smtp_client = smtplib.SMTP_SSL(
                    self._configuration.host,
                    self._configuration.port,
                    timeout=self._configuration.timeout_seconds,
                    context=ssl.create_default_context(),
                )
            else:
                smtp_client = smtplib.SMTP(
                    self._configuration.host,
                    self._configuration.port,
                    timeout=self._configuration.timeout_seconds,
                )

            with smtp_client:
                smtp_client.ehlo()

                if self._configuration.use_tls:
                    smtp_client.starttls(
                        context=ssl.create_default_context()
                    )
                    smtp_client.ehlo()

                if self._configuration.username:
                    smtp_client.login(
                        self._configuration.username,
                        self._configuration.password,
                    )

                smtp_client.send_message(
                    message,
                    from_addr=email_job.sender_email,
                    to_addrs=[email_job.recipient_email],
                )

        except (
            OSError,
            smtplib.SMTPException,
        ) as exc:
            raise SmtpSubmissionError(
                str(exc)
            ) from exc

        return str(message["Message-ID"])

    def _build_message(
        self,
        email_job: EmailJob,
    ) -> EmailMessage:
        message = EmailMessage()

        message["From"] = formataddr(
            (
                email_job.sender_name,
                email_job.sender_email,
            )
        )

        message["To"] = formataddr(
            (
                email_job.recipient_name or "",
                email_job.recipient_email,
            )
        )

        message["Subject"] = self._safe_header(
            email_job.subject
        )

        message["Date"] = formatdate(
            localtime=False
        )

        message["Message-ID"] = make_msgid(
            domain=self._configuration.message_id_domain
        )

        for name, value in email_job.custom_headers.items():
            if not name.lower().startswith("x-"):
                continue

            message[name] = self._safe_header(value)

        text_body = (
            email_job.text_body
            or "Ce message nécessite un client compatible HTML."
        )

        message.set_content(text_body)

        if email_job.html_body:
            message.add_alternative(
                email_job.html_body,
                subtype="html",
            )

        return message

    @staticmethod
    def _safe_header(
        value: str,
    ) -> str:
        if "\r" in value or "\n" in value:
            raise SmtpSubmissionError(
                "Un en-tête contient un retour à la ligne interdit."
            )

        return value.strip()