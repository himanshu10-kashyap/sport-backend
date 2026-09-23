"""add app_settings table

Revision ID: d4e5f6a7b8c9
Revises: b3f4a5c6d7e8
Create Date: 2026-09-23 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'b3f4a5c6d7e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
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
        "VALUES ('api_rate_limit_seconds', '2') "
        "ON CONFLICT (key) DO NOTHING"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_app_settings_key", table_name="app_settings")
    op.drop_table("app_settings")