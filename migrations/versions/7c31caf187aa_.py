"""empty message

Revision ID: 7c31caf187aa
Revises: 068dba61a274
Create Date: 2024-07-25 00:52:47.185424

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7c31caf187aa'
down_revision = '068dba61a274'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('messages',
    sa.Column('message_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('sender_id', sa.Integer(), nullable=True),
    sa.Column('recipient_id', sa.Integer(), nullable=True),
    sa.Column('subject', sa.String(length=255), nullable=True),
    sa.Column('body', sa.Text(), nullable=True),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['recipient_id'], ['user.user_id'], ),
    sa.ForeignKeyConstraint(['sender_id'], ['user.user_id'], ),
    sa.PrimaryKeyConstraint('message_id')
    )
    op.drop_table('message')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('message',
    sa.Column('message_id', sa.INTEGER(), nullable=False),
    sa.Column('sender_id', sa.INTEGER(), nullable=True),
    sa.Column('recipient_id', sa.INTEGER(), nullable=True),
    sa.Column('subject', sa.VARCHAR(length=255), nullable=True),
    sa.Column('body', sa.TEXT(), nullable=True),
    sa.Column('timestamp', sa.DATETIME(), nullable=True),
    sa.ForeignKeyConstraint(['recipient_id'], ['user.user_id'], ),
    sa.ForeignKeyConstraint(['sender_id'], ['user.user_id'], ),
    sa.PrimaryKeyConstraint('message_id')
    )
    op.drop_table('messages')
    # ### end Alembic commands ###
