"""add link screen status to advertisements

Revision ID: d1e2f3a4b5c6
Revises: b8c9d0e1f2a3
Create Date: 2026-09-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


advertisement_status = postgresql.ENUM(
    "ACTIVE", "INACTIVE", name="advertisement_status"
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    advertisement_status.create(bind, checkfirst=True)

    op.add_column(
        "advertisements",
        sa.Column("link", sa.String(length=500), nullable=True),
    )

    op.add_column(
        "advertisements",
        sa.Column("screen", sa.String(length=50), nullable=True),
    )
    op.execute(
        "UPDATE advertisements SET screen = 'home' WHERE screen IS NULL"
    )
    op.alter_column(
        "advertisements",
        "screen",
        existing_type=sa.String(length=50),
        nullable=False,
    )
    op.create_index(
        "ix_advertisements_screen", "advertisements", ["screen"], unique=False
    )

    op.add_column(
        "advertisements",
        sa.Column("status", advertisement_status, nullable=True),
    )
    op.execute(
        "UPDATE advertisements SET status = 'ACTIVE' WHERE status IS NULL"
    )
    op.alter_column(
        "advertisements",
        "status",
        existing_type=advertisement_status,
        nullable=False,
        server_default=sa.text("'ACTIVE'::advertisement_status"),
    )
    op.create_index(
        "ix_advertisements_status", "advertisements", ["status"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_advertisements_status", table_name="advertisements")
    op.drop_index("ix_advertisements_screen", table_name="advertisements")
    op.drop_column("advertisements", "status")
    op.drop_column("advertisements", "screen")
    op.drop_column("advertisements", "link")
    advertisement_status.drop(op.get_bind(), checkfirst=True)
