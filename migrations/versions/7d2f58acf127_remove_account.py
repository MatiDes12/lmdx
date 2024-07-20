"""remove account

Revision ID: 7d2f58acf127
Revises: 4c7c787b12f5
Create Date: 2024-07-19 20:36:42.271920

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7d2f58acf127'
down_revision = '4c7c787b12f5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('client_accounts')
    op.drop_table('doctor_accounts')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('doctor_accounts',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('full_name', sa.VARCHAR(length=100), nullable=False),
    sa.Column('email', sa.VARCHAR(length=120), nullable=False),
    sa.Column('special_email', sa.VARCHAR(length=120), nullable=False),
    sa.Column('specialization', sa.VARCHAR(length=120), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('special_email')
    )
    op.create_table('client_accounts',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('first_name', sa.VARCHAR(length=50), nullable=False),
    sa.Column('last_name', sa.VARCHAR(length=50), nullable=False),
    sa.Column('email', sa.VARCHAR(length=120), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    # ### end Alembic commands ###