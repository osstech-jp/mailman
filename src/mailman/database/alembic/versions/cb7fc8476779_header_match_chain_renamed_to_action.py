"""HeaderMatch chain renamed to action

Revision ID: cb7fc8476779
Revises: d4fbb4fd34ca
Create Date: 2016-02-02 17:23:36.199207

"""

# revision identifiers, used by Alembic.
revision = 'cb7fc8476779'
down_revision = 'd4fbb4fd34ca'

import sqlalchemy as sa
from alembic import op
from mailman.database.helpers import is_sqlite, exists_in_db
from mailman.database.types import Enum
from mailman.interfaces.action import Action


# Don't import the table definition from the models, it may break this
# migration when the model is updated in the future (see the Alembic doc)
hm_table = sa.sql.table('headermatch',
    sa.sql.column('action', Enum(Action)),
    sa.sql.column('chain', sa.VARCHAR())
    )


def upgrade():
    if not exists_in_db(op.get_bind(), 'headermatch', 'action'):
        op.add_column(
            'headermatch', sa.Column('action', Enum(Action), nullable=True))

    # Now migrate the data
    for action_enum in Action:
        op.execute(hm_table.update(
            ).values(action=action_enum
            ).where(hm_table.c.chain == action_enum.name))
    # Now that data is migrated, drop the old column (except on SQLite which
    # does not support this)
    if not is_sqlite(op.get_bind()):
        op.drop_column('headermatch', 'chain')


def downgrade():
    if not exists_in_db(op.get_bind(), 'headermatch', 'chain'):
        op.add_column(
            'headermatch', sa.Column('chain', sa.VARCHAR(), nullable=True))

    # Now migrate the data
    for action_enum in Action:
        op.execute(hm_table.update(
            ).values(chain=action_enum.name
            ).where(hm_table.c.action == action_enum))
    # Now that data is migrated, drop the new column (except on SQLite which
    # does not support this)
    if not is_sqlite(op.get_bind()):
        op.drop_column('headermatch', 'action')
