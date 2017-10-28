"""further_increase_pendedkeyvalue_value_size

Revision ID: 3f31035ed0d7
Revises: 4bd95c99b2e7
Create Date: 2017-10-18 17:42:35.550686

"""

from alembic import op
from mailman.database.types import SAUnicodeLarge, SAUnicodeXL


# revision identifiers, used by Alembic.
revision = '3f31035ed0d7'
down_revision = '4bd95c99b2e7'


def upgrade():
    # pendedkeyvalue table values can be much larger than SAUnicodeLarge
    with op.batch_alter_table('pendedkeyvalue') as batch_op:
        # Drop the existing index on the table.
        batch_op.drop_index(op.f('ix_pendedkeyvalue_value'))
        # Alter the column type and then create a new index with
        # mysql_length set to a fixed length value.
        batch_op.alter_column('value', type_=SAUnicodeXL)
        batch_op.create_index(op.f('ix_pendedkeyvalue_value'),
                              columns=['value'], mysql_length=100)


def downgrade():
    with op.batch_alter_table('pendedkeyvalue') as batch_op:
        batch_op.alter_column('value', type_=SAUnicodeLarge)
        # Drop the existing index because it has a fixed length value and then
        # re-create without the length constraint.
        batch_op.drop_index(op.f('ix_pendedkeyvalue_value'))
        batch_op.create_index(op.f('ix_pendedkeyvalue_value'),
                              columns=['value'])
