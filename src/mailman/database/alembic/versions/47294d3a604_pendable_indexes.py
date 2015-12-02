"""Pendable indexes

Add indexes on Pendable fields that can be queried upon.


Revision ID: 47294d3a604
Revises: 33bc0099223
Create Date: 2015-12-02 11:46:47.295174

"""

# revision identifiers, used by Alembic.
revision = '47294d3a604'
down_revision = '33bc0099223'

from alembic import op


def upgrade():
    op.create_index(
        op.f('ix_pended_expiration_date'), 'pended', ['expiration_date'],
        unique=False)
    op.create_index(op.f('ix_pended_token'), 'pended', ['token'], unique=False)
    op.create_index(
        op.f('ix_pendedkeyvalue_key'), 'pendedkeyvalue', ['key'], unique=False)
    op.create_index(
        op.f('ix_pendedkeyvalue_value'), 'pendedkeyvalue', ['value'],
        unique=False)


def downgrade():
    op.drop_index(op.f('ix_pendedkeyvalue_value'), table_name='pendedkeyvalue')
    op.drop_index(op.f('ix_pendedkeyvalue_key'), table_name='pendedkeyvalue')
    op.drop_index(op.f('ix_pended_token'), table_name='pended')
    op.drop_index(op.f('ix_pended_expiration_date'), table_name='pended')
