from __future__ import annotations

import uuid

from sqlalchemy import select

from extensions import db
from models.user import User


# ---------------------------
# User repository
# ---------------------------

class UserRepository:
    def get_by_id(
        self,
        user_id: uuid.UUID,
    ) -> User | None:
        return db.session.get(
            User,
            user_id,
        )

    def get_by_email(
        self,
        email: str,
    ) -> User | None:
        normalized_email = email.strip().lower()

        return db.session.execute(
            select(User).where(
                User.email == normalized_email
            )
        ).scalar_one_or_none()

    def email_exists(
        self,
        email: str,
    ) -> bool:
        normalized_email = email.strip().lower()

        user_id = db.session.execute(
            select(User.id)
            .where(
                User.email == normalized_email
            )
            .limit(1)
        ).scalar_one_or_none()

        return user_id is not None

    def add(
        self,
        user: User,
    ) -> User:
        db.session.add(user)
        db.session.flush()

        return user