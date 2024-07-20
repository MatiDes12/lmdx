"""add email

Revision ID: 8451cf9fa3da
Revises: 7d2f58acf127
Create Date: 2024-07-19 20:54:42.373291

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8451cf9fa3da'
down_revision = '7d2f58acf127'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('doctor', schema=None) as batch_op:
        batch_op.add_column(sa.Column('special_email', sa.String(length=120), nullable=False))
        batch_op.create_unique_constraint(None, ['special_email'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('doctor', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='unique')
        batch_op.drop_column('special_email')

    # ### end Alembic commands ###
