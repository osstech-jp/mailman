"""Add a numerical index to sort header matches.

Revision ID: d4fbb4fd34ca
Revises: bfda02ab3a9b
Create Date: 2016-02-01 15:57:09.807678

"""

# revision identifiers, used by Alembic.
revision = 'd4fbb4fd34ca'
down_revision = 'bfda02ab3a9b'

import sqlalchemy as sa
from alembic import op
from mailman.database.helpers import is_sqlite


def upgrade():
    op.add_column(
        'headermatch', sa.Column('index', sa.Integer(), nullable=True))
    if not is_sqlite(op.get_bind()):
        op.alter_column(
            'headermatch', 'mailing_list_id',
            existing_type=sa.INTEGER(), nullable=False)
    op.create_index(
        op.f('ix_headermatch_index'), 'headermatch', ['index'], unique=False)
    op.create_index(
        op.f('ix_headermatch_mailing_list_id'), 'headermatch',
        ['mailing_list_id'], unique=False)


def downgrade():
    op.drop_index(
        op.f('ix_headermatch_mailing_list_id'), table_name='headermatch')
    op.drop_index(op.f('ix_headermatch_index'), table_name='headermatch')
    if not is_sqlite(op.get_bind()):
        op.alter_column(
            'headermatch', 'mailing_list_id',
            existing_type=sa.INTEGER(), nullable=True)
        op.drop_column('headermatch', 'index')
