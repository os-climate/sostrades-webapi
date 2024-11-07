"""
add oauth state management

Revision ID: 23659f27ce8a
Revises: 26c265508f79
Create Date: 2022-05-17 10:29:40.233373

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "23659f27ce8a"
down_revision = "26c265508f79"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table("o_auth_state",
    sa.Column("id", sa.Integer(), nullable=False),
    sa.Column("is_active", sa.Boolean(), nullable=True),
    sa.Column("is_invalidated", sa.Boolean(), nullable=True),
    sa.Column("state", sa.String(length=64), nullable=False),
    sa.Column("creation_date", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=True),
    sa.Column("check_date", sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint("id"),
    sqlite_autoincrement=True,
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("o_auth_state")
    # ### end Alembic commands ###
