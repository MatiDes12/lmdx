"""empty message

Revision ID: 746f4e8fb62b
Revises: 3104b1cfb20c
Create Date: 2024-07-18 18:32:04.639901

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '746f4e8fb62b'
down_revision = '3104b1cfb20c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('doctor', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(length=20), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('doctor', schema=None) as batch_op:
        batch_op.drop_column('status')

    # ### end Alembic commands ###
