"""merge email auth and lesson routes migrations

Revision ID: c2b6c34132fa
Revises: 0dd717701f7f, bb6b79a3a998
Create Date: 2026-08-18 15:33:49.814113

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
# Autogenerate emits sqlmodel.sql.sqltypes.AutoString() for every str column,
# but Alembic's stock template does not import sqlmodel - so a generated
# revision raises NameError the first time it runs. Imported unconditionally
# here; an unused import in a revision file is harmless, a broken migration is
# not.
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'c2b6c34132fa'
down_revision: Union[str, Sequence[str], None] = ('0dd717701f7f', 'bb6b79a3a998')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
