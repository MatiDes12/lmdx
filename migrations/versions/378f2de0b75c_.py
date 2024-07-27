"""empty message

Revision ID: 378f2de0b75c
Revises: b3a1a995b4c7
Create Date: 2024-07-25 23:39:08.753080

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '378f2de0b75c'
down_revision = 'b3a1a995b4c7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('visit',
    sa.Column('visit_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=True),
    sa.Column('doctor_name', sa.String(length=255), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('summary', sa.Text(), nullable=True),
    sa.Column('next_steps', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.patient_id'], ),
    sa.PrimaryKeyConstraint('visit_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('visit')
    # ### end Alembic commands ###