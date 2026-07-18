from __future__ import annotations

import secrets

from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)


# ---------------------------
# Argon2 configuration
# ---------------------------

_PASSWORD_HASHER = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)

_DUMMY_PASSWORD_HASH = _PASSWORD_HASHER.hash(
    secrets.token_urlsafe(32)
)


# ---------------------------
# Password service
# ---------------------------

class PasswordService:
    def hash(
        self,
        password: str,
    ) -> str:
        self.validate_strength(
            password
        )

        return _PASSWORD_HASHER.hash(
            password
        )

    def verify(
        self,
        *,
        password_hash: str,
        password: str,
    ) -> bool:
        try:
            return _PASSWORD_HASHER.verify(
                password_hash,
                password,
            )
        except (
            InvalidHashError,
            VerificationError,
            VerifyMismatchError,
        ):
            return False

    def verify_dummy(
        self,
        password: str,
    ) -> None:
        try:
            _PASSWORD_HASHER.verify(
                _DUMMY_PASSWORD_HASH,
                password,
            )
        except (
            InvalidHashError,
            VerificationError,
            VerifyMismatchError,
        ):
            pass

    def needs_rehash(
        self,
        password_hash: str,
    ) -> bool:
        try:
            return _PASSWORD_HASHER.check_needs_rehash(
                password_hash
            )
        except InvalidHashError:
            return True

    @staticmethod
    def validate_strength(
        password: str,
    ) -> None:
        if len(password) < 12:
            raise ValueError(
                "password_too_short"
            )

        if len(password) > 128:
            raise ValueError(
                "password_too_long"
            )

        character_groups = sum(
            [
                any(
                    character.islower()
                    for character in password
                ),
                any(
                    character.isupper()
                    for character in password
                ),
                any(
                    character.isdigit()
                    for character in password
                ),
                any(
                    not character.isalnum()
                    for character in password
                ),
            ]
        )

        if character_groups < 3:
            raise ValueError(
                "password_not_complex_enough"
            )