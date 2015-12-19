"""digests

Revision ID: 70af5a4e5790
Revises: 47294d3a604
Create Date: 2015-12-19 12:05:42.202998

"""

# revision identifiers, used by Alembic.
revision = '70af5a4e5790'
down_revision = '47294d3a604'

from alembic import op
import sqlalchemy as sa


def upgrade():
    with op.batch_alter_table('mailinglist') as batch_op:
        batch_op.alter_column('digestable', new_column_name='digests_enabled')
        batch_op.drop_column('nondigestable')


def downgrade():
    with op.batch_alter_table('mailinglist') as batch_op:
        batch_op.alter_column('digests_enabled', new_column_name='digestable')
        # The data for this column is lost, it's not used anyway.
        batch_op.add_column(sa.Column('nondigestable', sa.Boolean))
