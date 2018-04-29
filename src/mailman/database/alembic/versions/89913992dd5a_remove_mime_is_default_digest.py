"""remove mime_is_default_digest

Revision ID: 89913992dd5a
Revises: 448a93984c35
Create Date: 2016-10-31 09:21:24.941438

"""

import sqlalchemy as sa

from alembic import op
from mailman.database.helpers import exists_in_db, is_sqlite


# revision identifiers, used by Alembic.
revision = '89913992dd5a'
down_revision = 'dfe82cf73702'


def upgrade():
    if not is_sqlite(op.get_bind()):
        # SQLite does not support dropping columns.
        op.drop_column(                                       # pragma: nocover
            'mailinglist', 'mime_is_default_digest')          # pragma: nocover


def downgrade():
    if not exists_in_db(
            op.get_bind(), 'mailinglist', 'mime_is_default_digest'):
        op.add_column(
            'mailinglist',
            sa.Column('mime_is_default_digest', sa.BOOLEAN(), nullable=True))
