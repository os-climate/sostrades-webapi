"""
Add study case logging table

Revision ID: d341b6f43c5b
Revises: ead421cc5deb
Create Date: 2022-07-26 11:07:28.253405

"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "d341b6f43c5b"
down_revision = "ead421cc5deb"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table("study_case_log",
    sa.Column("id", sa.Integer(), nullable=False),
    sa.Column("study_case_id", sa.Integer(), nullable=True),
    sa.Column("name", sa.Text(), nullable=True),
    sa.Column("log_level_name", sa.String(length=64), nullable=True),
    sa.Column("created", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=True),
    sa.Column("message", sa.Text(), nullable=True),
    sa.Column("exception", sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(["study_case_id"], ["study_case.id"], name="fk_study_case_log_study_case_id", ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("id"),
    sqlite_autoincrement=True,
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("study_case_log")
    # ### end Alembic commands ###
