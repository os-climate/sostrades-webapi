"""Remove displine and type in studycaseValidationModel

Revision ID: 89b66a62d3a7
Revises: 35ba4ee9fc53
Create Date: 2022-02-02 10:45:32.800916

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '89b66a62d3a7'
down_revision = '35ba4ee9fc53'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('study_case_validation', 'discipline_name')
    op.drop_column('study_case_validation', 'validation_type')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('study_case_validation', sa.Column('validation_type', mysql.VARCHAR(length=64), nullable=True))
    op.add_column('study_case_validation', sa.Column('discipline_name', mysql.TEXT(), nullable=True))
    # ### end Alembic commands ###
