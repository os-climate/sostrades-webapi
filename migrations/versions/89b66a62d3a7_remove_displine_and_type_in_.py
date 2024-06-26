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
from sqlalchemy.dialects import mysql

"""Remove displine and type in studycaseValidationModel

Revision ID: 89b66a62d3a7
Revises: 35ba4ee9fc53
Create Date: 2022-02-02 10:45:32.800916

"""

# revision identifiers, used by Alembic.
revision = "89b66a62d3a7"
down_revision = "35ba4ee9fc53"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("study_case_validation", "discipline_name")
    op.drop_column("study_case_validation", "validation_type")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("study_case_validation", sa.Column("validation_type", mysql.VARCHAR(length=64), nullable=True))
    op.add_column("study_case_validation", sa.Column("discipline_name", mysql.TEXT(), nullable=True))
    # ### end Alembic commands ###
