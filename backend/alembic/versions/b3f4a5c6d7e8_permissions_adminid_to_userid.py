"""permissions adminid -> admins.userid

Revision ID: b3f4a5c6d7e8
Revises: a07620afd800
Create Date: 2026-09-23 13:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b3f4a5c6d7e8'
down_revision: Union[str, Sequence[str], None] = 'a07620afd800'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Drop old integer FK
    op.drop_constraint(
        "permissions_adminid_fkey", "permissions", type_="foreignkey"
    )

    # 2. Widen column to text first (integer -> text)
    op.alter_column(
        "permissions",
        "adminid",
        existing_type=sa.Integer(),
        type_=sa.String(36),
        existing_nullable=False,
        postgresql_using="adminid::text",
    )

    # 3. Migrate existing integer ids to the matching userid
    op.execute(
        "UPDATE permissions SET adminid = admins.userid::text "
        "FROM admins WHERE admins.id::text = permissions.adminid"
    )

    # 4. Change column type from text to uuid
    op.alter_column(
        "permissions",
        "adminid",
        existing_type=sa.String(36),
        type_=postgresql.UUID(as_uuid=True),
        existing_nullable=False,
        postgresql_using="adminid::uuid",
    )

    # 5. Recreate FK on admins.userid
    op.create_foreign_key(
        "permissions_adminid_fkey",
        "permissions",
        "admins",
        ["adminid"],
        ["userid"],
        ondelete="CASCADE",
        onupdate="CASCADE",
    )

    # 6. Align created/updated timestamps with the model (no timezone)
    op.alter_column(
        "permissions",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=True,
    )
    op.alter_column(
        "permissions",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "permissions_adminid_fkey", "permissions", type_="foreignkey"
    )

    op.execute(
        "UPDATE permissions SET adminid = admins.id::text "
        "FROM admins WHERE admins.userid::text = permissions.adminid::text"
    )

    op.alter_column(
        "permissions",
        "adminid",
        existing_type=postgresql.UUID(as_uuid=True),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="adminid::integer",
    )

    op.create_foreign_key(
        "permissions_adminid_fkey",
        "permissions",
        "admins",
        ["adminid"],
        ["id"],
        ondelete="CASCADE",
        onupdate="CASCADE",
    )

    op.alter_column(
        "permissions",
        "created_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
        postgresql_using="created_at::timestamptz",
    )
    op.alter_column(
        "permissions",
        "updated_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
        postgresql_using="updated_at::timestamptz",
    )