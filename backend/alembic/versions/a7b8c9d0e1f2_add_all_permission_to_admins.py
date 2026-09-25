from typing import Sequence, Union

from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE permissions
        SET permission = 'ALL'
        FROM admins
        WHERE permissions.userid = admins.userid
          AND UPPER(admins.role) = 'ADMIN'
          AND UPPER(permissions.permission) = 'ALL'
          AND permissions.permission <> 'ALL'
        """
    )
    op.execute(
        """
        INSERT INTO permissions (userid, permission)
        SELECT admins.userid, 'ALL'
        FROM admins
        WHERE UPPER(admins.role) = 'ADMIN'
          AND NOT EXISTS (
              SELECT 1
              FROM permissions
              WHERE permissions.userid = admins.userid
                AND UPPER(permissions.permission) = 'ALL'
          )
        """
    )


def downgrade() -> None:
    pass
