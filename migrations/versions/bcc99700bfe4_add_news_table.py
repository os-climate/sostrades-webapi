"""Add news table

Revision ID: bcc99700bfe4
Revises: cbf661e68ff3
Create Date: 2022-09-07 10:39:39.317998

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bcc99700bfe4'
down_revision = 'cbf661e68ff3'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('news',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('message', sa.String(length=300), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('creation_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('last_modification_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name='fk_news_user_id'),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('news')
    # ### end Alembic commands ###
