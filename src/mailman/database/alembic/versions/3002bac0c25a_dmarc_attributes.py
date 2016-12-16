"""dmarc_attributes

Revision ID: 3002bac0c25a
Revises: 448a93984c35
Create Date: 2016-10-30 22:05:17.881880

"""

import sqlalchemy as sa

from alembic import op
from mailman.database.helpers import exists_in_db
from mailman.database.types import Enum, SAUnicode
from mailman.interfaces.mailinglist import DMARCModerationAction, FromIsList


# revision identifiers, used by Alembic.
revision = '3002bac0c25a'
down_revision = '448a93984c35'


def upgrade():
    if not exists_in_db(op.get_bind(),
                        'mailinglist',
                        'dmarc_moderation_action'
                        ):
        # SQLite may not have removed it when downgrading.  It should be OK
        # to just test one.
        op.add_column('mailinglist', sa.Column(
            'dmarc_moderation_action',
            Enum(DMARCModerationAction),
            nullable=True))
        op.add_column('mailinglist', sa.Column(
            'dmarc_quarantine_moderation_action',
            sa.Boolean(),
            nullable=True))
        op.add_column('mailinglist', sa.Column(
            'dmarc_none_moderation_action',
            sa.Boolean(),
            nullable=True))
        op.add_column('mailinglist', sa.Column(
            'dmarc_moderation_notice',
            SAUnicode(),
            nullable=True))
        op.add_column('mailinglist', sa.Column(
            'dmarc_wrapped_message_text',
            SAUnicode(),
            nullable=True))
        op.add_column('mailinglist', sa.Column(
            'from_is_list',
            Enum(FromIsList),
            nullable=True))
    # Now migrate the data.  Don't import the table definition from the
    # models, it may break this migration when the model is updated in the
    # future (see the Alembic doc).
    mlist = sa.sql.table(
        'mailinglist',
        sa.sql.column('dmarc_moderation_action', Enum(DMARCModerationAction)),
        sa.sql.column('dmarc_quarantine_moderation_action', sa.Boolean()),
        sa.sql.column('dmarc_none_moderation_action', sa.Boolean()),
        sa.sql.column('dmarc_moderation_notice', SAUnicode()),
        sa.sql.column('dmarc_wrapped_message_text', SAUnicode()),
        sa.sql.column('from_is_list', Enum(FromIsList))
        )
    # These are all new attributes so just set defaults.
    op.execute(mlist.update().values(dict(
        dmarc_moderation_action=op.inline_literal(DMARCModerationAction.none),
        dmarc_quarantine_moderation_action=op.inline_literal(True),
        dmarc_none_moderation_action=op.inline_literal(False),
        dmarc_moderation_notice=op.inline_literal(''),
        dmarc_wrapped_message_text=op.inline_literal(''),
        from_is_list=op.inline_literal(FromIsList.none),
        )))


def downgrade():
    with op.batch_alter_table('mailinglist') as batch_op:
        batch_op.drop_column('dmarc_moderation_action')
        batch_op.drop_column('dmarc_quarantine_moderation_action')
        batch_op.drop_column('dmarc_none_moderation_action')
        batch_op.drop_column('dmarc_moderation_notice')
        batch_op.drop_column('dmarc_wrapped_message_text')
        batch_op.drop_column('from_is_list')
