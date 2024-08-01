"""Add Notification model

Revision ID: 6832cfa3608a
Revises: fb20be38b7e0
Create Date: 2024-07-31 13:18:49.078660

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6832cfa3608a'
down_revision = 'fb20be38b7e0'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('notification', schema=None) as batch_op:
        batch_op.add_column(sa.Column('notification_type', sa.String(length=50), nullable=False))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('notification', schema=None) as batch_op:
        batch_op.drop_column('notification_type')

    # ### end Alembic commands ###
