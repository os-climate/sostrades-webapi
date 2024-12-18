"""
add link model

Revision ID: 9dce152cd92c
Revises: aede0731db6b
Create Date: 2022-03-03 12:17:18.079065

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9dce152cd92c"
down_revision = "aede0731db6b"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table("link",
    sa.Column("id", sa.Integer(), nullable=False),
    sa.Column("url", sa.String(length=512), nullable=False),
    sa.Column("label", sa.String(length=64), nullable=False),
    sa.Column("description", sa.String(length=300), nullable=False),
    sa.Column("user_id", sa.Integer(), nullable=True),
    sa.Column("last_modified", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=True),
    sa.ForeignKeyConstraint(["user_id"], ["user.id"], name="fk_link_user_id"),
    sa.PrimaryKeyConstraint("id"),
    sqlite_autoincrement=True,
    )
    op.create_index(op.f("ix_link_url"), "link", ["url"], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_link_url"), table_name="link")
    op.drop_table("link")
    # ### end Alembic commands ###
