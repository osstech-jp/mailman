"""add tag column

Revision ID: 2d2d0ef0828f
Revises: 15401063d4e3
Create Date: 2019-04-27 08:58:48.496854

"""

import sqlalchemy as sa

from alembic import op
from mailman.database.helpers import exists_in_db, is_sqlite
from mailman.database.types import SAUnicode


# revision identifiers, used by Alembic.
revision = '2d2d0ef0828f'
down_revision = '15401063d4e3'


def upgrade():
    if not exists_in_db(op.get_bind(), 'headermatch', 'tag'):
        # SQLite may not have removed it when downgrading.
        op.add_column(
            'headermatch',
            sa.Column('tag', type_=SAUnicode, nullable=True))


def downgrade():
    if not is_sqlite(op.get_bind()):
        # diffcov runs with SQLite so this isn't covered.
        op.drop_column('headermatch', 'tag')        # pragma: nocover
