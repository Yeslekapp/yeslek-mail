"""Add full_name column to users.

Revision ID: 20260718_add_full_name
Revises:
Create Date: 2026-07-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# ---------------------------
# Alembic identifiers
# ---------------------------

revision: str = "20260718_add_full_name"
down_revision: str | None = None
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


# ---------------------------
# Migration upgrade
# ---------------------------

def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("users")
    }

    if "full_name" not in existing_columns:
        op.add_column(
            "users",
            sa.Column(
                "full_name",
                sa.String(length=120),
                nullable=True,
            ),
        )

    op.execute(
        sa.text(
            """
            UPDATE users
            SET full_name = 'Utilisateur'
            WHERE full_name IS NULL
               OR BTRIM(full_name) = ''
            """
        )
    )

    op.alter_column(
        "users",
        "full_name",
        existing_type=sa.String(length=120),
        nullable=False,
    )


# ---------------------------
# Migration downgrade
# ---------------------------

def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("users")
    }

    if "full_name" in existing_columns:
        op.drop_column(
            "users",
            "full_name",
        )