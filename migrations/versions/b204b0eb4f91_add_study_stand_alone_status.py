"""add study stand alone status

Revision ID: b204b0eb4f91
Revises: 6d471f14fb35
Create Date: 2025-03-31 17:27:39.247105

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'b204b0eb4f91'
down_revision = '6d471f14fb35'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('study_stand_alone_status',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('study_case_id', sa.Integer(), nullable=False),
    sa.Column('progress', sa.Integer(), nullable=True),
    sa.Column('next_progress', sa.Integer(), nullable=True),
    sa.Column('progress_text', sa.String(length=128), server_default='', nullable=True),
    sa.Column('is_finished', sa.Boolean(), nullable=False),
    sa.Column('is_in_error', sa.Boolean(), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['study_case_id'], ['study_case.id'], name='fk_study_stand_alone_status_study_case_id', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    # with op.batch_alter_table('group', schema=None) as batch_op:
    #     batch_op.drop_column('is_keycloak_group')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    # with op.batch_alter_table('group', schema=None) as batch_op:
    #     batch_op.add_column(sa.Column('is_keycloak_group', mysql.TINYINT(display_width=1), server_default=sa.text("'0'"), autoincrement=False, nullable=True))

    op.drop_table('study_stand_alone_status')
    # ### end Alembic commands ###
