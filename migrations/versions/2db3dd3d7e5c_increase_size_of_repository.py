"""Increase size of repository

Revision ID: 2db3dd3d7e5c
Revises: 6742a7abbc12
Create Date: 2024-08-08 18:43:41.524297

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '2db3dd3d7e5c'
down_revision = '6742a7abbc12'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('study_case', schema=None) as batch_op:
        batch_op.alter_column('repository',
               existing_type=mysql.VARCHAR(length=64),
               type_=mysql.VARCHAR(length=128),
               existing_nullable=True,
               existing_server_default=sa.text("'test'"))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('study_case', schema=None) as batch_op:
        batch_op.alter_column('repository',
               existing_type=mysql.VARCHAR(length=128),
               type_=mysql.VARCHAR(length=64),
               existing_nullable=True,
               existing_server_default=sa.text("'test'"))

    # ### end Alembic commands ###