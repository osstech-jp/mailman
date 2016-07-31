"""unsubscription_workflow

Revision ID: 448a93984c35
Revises: 7b254d88f122
Create Date: 2016-06-02 14:34:24.154723

"""

# revision identifiers, used by Alembic.
revision = '448a93984c35'
down_revision = '7b254d88f122'

import sqlalchemy as sa
from alembic import op
from mailman.database.helpers import is_sqlite, exists_in_db
from mailman.database.types import Enum
from mailman.interfaces.mailinglist import SubscriptionPolicy

def upgrade():
    if not exists_in_db(op.get_bind(), 'mailinglist', 'unsubscription_policy'):
        # SQLite may not have removed it when downgrading.
        op.add_column('mailinglist', sa.Column(
            'unsubscription_policy', Enum(SubscriptionPolicy), nullable=True))

        # Now migrate the data.  Don't import the table definition from the
        # models, it may break this migration when the model is updated in the
        # future (see the Alembic doc).
        mlist = sa.sql.table(
            'mailinglist',
            sa.sql.column('unsubscription_policy', Enum(SubscriptionPolicy))
        )
        # There were no enforced subscription policy before, so all lists are
        # considered open.
        op.execute(mlist.update().values(
            {'unsubscription_policy':
             op.inline_literal(SubscriptionPolicy.open)}))


def downgrade():
    if not is_sqlite(op.get_bind()):
        # SQLite does not support dropping columns.
        op.drop_column('mailinglist', 'unsubscription_policy')
