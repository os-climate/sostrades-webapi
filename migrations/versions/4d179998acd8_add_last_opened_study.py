'''
Copyright 2022 Airbus SAS
Modifications on 2024/06/07 Copyright 2024 Capgemini
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

'''
import sqlalchemy as sa
from alembic import op

"""Add last opened study

Revision ID: 4d179998acd8
Revises: fb0a1fde7fe0
Create Date: 2022-12-07 14:34:47.294663

"""

# revision identifiers, used by Alembic.
revision = "4d179998acd8"
down_revision = "fb0a1fde7fe0"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table("user_last_opened_study",
    sa.Column("id", sa.Integer(), nullable=False),
    sa.Column("user_id", sa.Integer(), nullable=False),
    sa.Column("study_case_id", sa.Integer(), nullable=False),
    sa.Column("opening_date", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=True),
    sa.ForeignKeyConstraint(["study_case_id"], ["study_case.id"], name="fk_user_study_last_opened_study_case_id", ondelete="CASCADE"),
    sa.ForeignKeyConstraint(["user_id"], ["user.id"], name="fk_user_study_last_opened_user_id", ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("user_last_opened_study")
    # ### end Alembic commands ###
