"""add_alias_domain

Revision ID: dfe82cf73702
Revises: fa0d96e28631
Create Date: 2016-10-07 16:50:53.368932

"""

import sqlalchemy as sa

from alembic import op
from mailman.database.helpers import exists_in_db
from mailman.database.types import SAUnicode


# revision identifiers, used by Alembic.
revision = 'dfe82cf73702'
down_revision = '3f31035ed0d7'


def upgrade():
    if not exists_in_db(op.get_bind(), 'domain', 'alias_domain'):
        op.add_column(
            'domain', sa.Column('alias_domain', SAUnicode, nullable=True)
            )


def downgrade():
    with op.batch_alter_table('domain') as batch_op:
        batch_op.drop_column('alias_domain')
