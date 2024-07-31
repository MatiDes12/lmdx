"""empty message

Revision ID: 6864d5c66704
Revises: 0b4bdc8b6b2e
Create Date: 2024-07-31 01:27:14.848904

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6864d5c66704'
down_revision = '0b4bdc8b6b2e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('username',
               existing_type=sa.VARCHAR(length=50),
               nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('username',
               existing_type=sa.VARCHAR(length=50),
               nullable=True)

    # ### end Alembic commands ###
