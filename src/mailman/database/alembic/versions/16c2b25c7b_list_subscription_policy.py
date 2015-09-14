"""List subscription policy

Revision ID: 16c2b25c7b
Revises: 46e92facee7
Create Date: 2015-03-21 11:00:44.634883

"""

# revision identifiers, used by Alembic.
revision = '16c2b25c7b'
down_revision = '46e92facee7'

from alembic import op
import sqlalchemy as sa

from mailman.database.types import Enum
from mailman.database.helpers import is_sqlite, exists_in_db
from mailman.interfaces.mailinglist import SubscriptionPolicy


def upgrade():

    ### Update the schema
    if not exists_in_db(op.get_bind(), 'mailinglist', 'subscription_policy'):
        # SQLite may not have removed it when downgrading.
        op.add_column('mailinglist', sa.Column(
            'subscription_policy', Enum(SubscriptionPolicy), nullable=True))

    ### Now migrate the data
    # don't import the table definition from the models, it may break this
    # migration when the model is updated in the future (see the Alembic doc)
    mlist = sa.sql.table('mailinglist',
        sa.sql.column('subscription_policy', Enum(SubscriptionPolicy))
        )
    # there were no enforced subscription policy before, so all lists are
    # considered open
    op.execute(mlist.update().values(
        {'subscription_policy': op.inline_literal(SubscriptionPolicy.open)}))


def downgrade():
    if not is_sqlite(op.get_bind()):
        # SQLite does not support dropping columns.
        op.drop_column('mailinglist', 'subscription_policy')
