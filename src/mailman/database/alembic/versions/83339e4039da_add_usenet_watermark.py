"""add_usenet_watermark

Revision ID: 83339e4039da
Revises: 2d2d0ef0828f
Create Date: 2019-07-17 20:41:39.601334

"""

import sqlalchemy as sa

from alembic import op
from mailman.database.helpers import exists_in_db


# revision identifiers, used by Alembic.
revision = '83339e4039da'
down_revision = '2d2d0ef0828f'


def upgrade():
    if not exists_in_db(op.get_bind(),
                        'mailinglist',
                        'usenet_watermark'
                        ):
        # SQLite may not have removed it when downgrading.
        op.add_column('mailinglist', sa.Column(
            'usenet_watermark',
            sa.Integer,
            nullable=True))


def downgrade():
    with op.batch_alter_table('mailinglist') as batch_op:
        batch_op.drop_column('usenet_watermark')
