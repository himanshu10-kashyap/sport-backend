from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _rename_not_null_constraint(old_name: str, new_name: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conrelid = to_regclass('permissions')
                  AND contype = 'n'
                  AND conname = '{old_name}'
            ) THEN
                EXECUTE
                    'ALTER TABLE permissions RENAME CONSTRAINT '
                    || quote_ident('{old_name}')
                    || ' TO '
                    || quote_ident('{new_name}');
            END IF;
        END
        $$
        """
    )


def upgrade() -> None:
    op.alter_column(
        "permissions",
        "adminid",
        new_column_name="userid",
        existing_type=postgresql.UUID(as_uuid=True),
        existing_nullable=False,
    )
    op.execute(
        "ALTER TABLE permissions "
        "RENAME CONSTRAINT permissions_adminid_fkey "
        "TO permissions_userid_fkey"
    )
    op.execute("ALTER INDEX ix_permissions_adminid RENAME TO ix_permissions_userid")
    _rename_not_null_constraint(
        "permissions_adminid_not_null",
        "permissions_userid_not_null",
    )


def downgrade() -> None:
    _rename_not_null_constraint(
        "permissions_userid_not_null",
        "permissions_adminid_not_null",
    )
    op.execute("ALTER INDEX ix_permissions_userid RENAME TO ix_permissions_adminid")
    op.execute(
        "ALTER TABLE permissions "
        "RENAME CONSTRAINT permissions_userid_fkey "
        "TO permissions_adminid_fkey"
    )
    op.alter_column(
        "permissions",
        "userid",
        new_column_name="adminid",
        existing_type=postgresql.UUID(as_uuid=True),
        existing_nullable=False,
    )
