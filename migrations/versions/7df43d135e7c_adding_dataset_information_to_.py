"""
adding dataset information to StudyCaseChange

Revision ID: 7df43d135e7c
Revises: 81ddc6b58939
Create Date: 2024-04-29 11:06:20.428697

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "7df43d135e7c"
down_revision = "81ddc6b58939"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("study_case_change", sa.Column("dataset_connector_id", mysql.TEXT(), nullable=True))
    op.add_column("study_case_change", sa.Column("dataset_id", mysql.TEXT(), nullable=True))
    op.add_column("study_case_change", sa.Column("dataset_parameter_id", mysql.TEXT(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("study_case_change", "dataset_parameter_id")
    op.drop_column("study_case_change", "dataset_id")
    op.drop_column("study_case_change", "dataset_connector_id")
    # ### end Alembic commands ###
