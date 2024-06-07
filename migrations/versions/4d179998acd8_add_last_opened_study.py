"""Add last opened study

Revision ID: 4d179998acd8
Revises: fb0a1fde7fe0
Create Date: 2022-12-07 14:34:47.294663

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4d179998acd8'
down_revision = 'fb0a1fde7fe0'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user_last_opened_study',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('study_case_id', sa.Integer(), nullable=False),
    sa.Column('opening_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['study_case_id'], ['study_case.id'], name='fk_user_study_last_opened_study_case_id', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name='fk_user_study_last_opened_user_id', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('user_last_opened_study')
    # ### end Alembic commands ###
