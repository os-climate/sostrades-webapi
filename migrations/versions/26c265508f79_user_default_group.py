"""User default group

Revision ID: 26c265508f79
Revises: 9dce152cd92c
Create Date: 2022-04-05 15:20:23.117422

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '26c265508f79'
down_revision = '9dce152cd92c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('default_group_id', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'default_group_id')
    # ### end Alembic commands ###