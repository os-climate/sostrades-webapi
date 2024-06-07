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

"""add link model

Revision ID: 9dce152cd92c
Revises: aede0731db6b
Create Date: 2022-03-03 12:17:18.079065

"""

# revision identifiers, used by Alembic.
revision = '9dce152cd92c'
down_revision = 'aede0731db6b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('link',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('url', sa.String(length=512), nullable=False),
    sa.Column('label', sa.String(length=64), nullable=False),
    sa.Column('description', sa.String(length=300), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('last_modified', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name='fk_link_user_id'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_link_url'), 'link', ['url'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_link_url'), table_name='link')
    op.drop_table('link')
    # ### end Alembic commands ###
