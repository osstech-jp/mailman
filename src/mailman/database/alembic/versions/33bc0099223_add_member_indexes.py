"""Add member indexes

Revision ID: 33bc0099223
Revises: 42756496720
Create Date: 2015-11-19 23:04:42.449553

"""

# Revision identifiers, used by Alembic.
revision = '33bc0099223'
down_revision = '42756496720'

from alembic import op


def upgrade():
    op.create_index(op.f('ix_member_address_id'),
                    'member', ['address_id'],
                    unique=False)
    op.create_index(op.f('ix_member_preferences_id'),
                    'member', ['preferences_id'],
                    unique=False)
    op.create_index(op.f('ix_member_user_id'),
                    'member', ['user_id'],
                    unique=False)
    op.create_index(op.f('ix_address_email'),
                    'address', ['email'],
                    unique=False)


def downgrade():
    op.drop_index(op.f('ix_address_email'), table_name='address')
    op.drop_index(op.f('ix_member_user_id'), table_name='member')
    op.drop_index(op.f('ix_member_preferences_id'), table_name='member')
    op.drop_index(op.f('ix_member_address_id'), table_name='member')
