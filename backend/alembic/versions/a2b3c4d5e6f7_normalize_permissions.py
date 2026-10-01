"""normalize permissions

Repair rows where a sub-admin holding "ALL" also carried individual
permissions (e.g. ALL + advertisement), collapse duplicates and canonicalise
the spelling of every value. Then guard the table so the mixed state cannot
come back.

Revision ID: a2b3c4d5e6f7
Revises: d1e2f3a4b5c6
Create Date: 2026-10-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDEX_NAME = "uq_permissions_userid_permission"


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("DELETE FROM permissions WHERE BTRIM(COALESCE(permission, '')) = ''")

    # "ALL" already covers every specific permission, so keep only the ALL row.
    op.execute(
        """
        DELETE FROM permissions AS specific
        USING permissions AS grant_all
        WHERE specific.userid = grant_all.userid
          AND UPPER(BTRIM(grant_all.permission)) = 'ALL'
          AND UPPER(BTRIM(specific.permission)) <> 'ALL'
        """
    )

    op.execute(
        """
        UPDATE permissions
        SET permission = 'ALL'
        WHERE UPPER(BTRIM(permission)) = 'ALL'
          AND permission <> 'ALL'
        """
    )

    op.execute(
        """
        UPDATE permissions
        SET permission = LOWER(BTRIM(permission))
        WHERE LOWER(BTRIM(permission)) IN ('rate_limit', 'advertisement')
          AND permission <> LOWER(BTRIM(permission))
        """
    )

    op.execute(
        """
        DELETE FROM permissions AS duplicate
        USING permissions AS keeper
        WHERE duplicate.userid = keeper.userid
          AND duplicate.permission = keeper.permission
          AND duplicate.id > keeper.id
        """
    )

    op.create_index(
        INDEX_NAME, "permissions", ["userid", "permission"], unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(INDEX_NAME, table_name="permissions")
