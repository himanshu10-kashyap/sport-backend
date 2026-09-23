"""rename app_settings -> rate_limit

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-23 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "rate_limit",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute(
        "INSERT INTO rate_limit (id, value) "
        "SELECT 1, CASE WHEN value ~ '^[0-9]+$' THEN value::int ELSE 2 END "
        "FROM app_settings WHERE key = 'api_rate_limit_seconds' "
        "ON CONFLICT (id) DO NOTHING"
    )

    op.execute(
        "INSERT INTO rate_limit (id, value) SELECT 1, 2 "
        "WHERE NOT EXISTS (SELECT 1 FROM rate_limit WHERE id = 1)"
    )

    op.drop_table("app_settings")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_app_settings_key", "app_settings", ["key"], unique=True)

    op.execute(
        "INSERT INTO app_settings (key, value) "
        "VALUES ('api_rate_limit_seconds', "
        "COALESCE((SELECT value::text FROM rate_limit WHERE id = 1), '2'))"
    )

    op.drop_table("rate_limit")