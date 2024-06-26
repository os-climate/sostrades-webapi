"""
Add information about deleting a column from a dataframe

Revision ID: 5e995cf0ba49
Revises: 4d179998acd8
Create Date: 2023-08-22 09:38:43.798515

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "5e995cf0ba49"
down_revision = "4d179998acd8"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("study_case_change", sa.Column("deleted_columns", mysql.TEXT(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("study_case_change", "deleted_columns")
    # ### end Alembic commands ###
