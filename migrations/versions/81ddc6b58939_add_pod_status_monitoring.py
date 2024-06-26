"""
add pod status monitoring

Revision ID: 81ddc6b58939
Revises: 18d8890a5e5f
Create Date: 2024-04-04 09:14:16.478947

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "81ddc6b58939"
down_revision = "18d8890a5e5f"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("reference_study", sa.Column("execution_thread_id", sa.Integer(), nullable=True))
    op.add_column("study_case_execution", sa.Column("message", sa.String(length=64), server_default="", nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("study_case_execution", "message")
    op.drop_column("reference_study", "execution_thread_id")
    # ### end Alembic commands ###
