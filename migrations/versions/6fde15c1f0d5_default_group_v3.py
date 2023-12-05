"""default_group_v3

Revision ID: 6fde15c1f0d5
Revises: 224990fccd32
Create Date: 2023-10-16 17:22:23.100757

"""
from alembic import op
import sqlalchemy as sa

from sos_trades_api.models.database_models import Group
from sos_trades_api.server.base_server import db

# revision identifiers, used by Alembic.
revision = '6fde15c1f0d5'
down_revision = '224990fccd32'
branch_labels = None
depends_on = None


def upgrade():
    try:
        # Retrieve the "all_users_group"
        all_users_group = Group.query.filter(Group.name == Group.ALL_USERS_GROUP).first()
        # Modify the "is_default_applicative_group" property of the group "all_users"
        all_users_group.is_default_applicative_group = False
        db.session.add(all_users_group)

        # Retrieve the "SosTradesDev"
        sostrades_dev_group = Group.query.filter(Group.name == Group.SOS_TRADES_DEV_GROUP).first()
        # Modify the "is_default_applicative_group" property of the group "SosTradesDev"
        sostrades_dev_group.is_default_applicative_group = True
        db.session.add(sostrades_dev_group)

        db.session.commit()
    except Exception as exc:
        db.session.rollback()


def downgrade():
    try:
        # Retrieve the "all_users_group"
        all_users_group = Group.query.filter(Group.name == Group.ALL_USERS_GROUP).first()
        # Modify the "is_default_applicative_group" property of the group "all_users"
        all_users_group.is_default_applicative_group = True
        db.session.add(all_users_group)

        # Retrieve the "SosTradesDev"
        sostrades_dev_group = Group.query.filter(Group.name == Group.SOS_TRADES_DEV_GROUP).first()
        # Modify the "is_default_applicative_group" property of the group "SosTradesDev"
        sostrades_dev_group.is_default_applicative_group = False
        db.session.add(sostrades_dev_group)

        db.session.commit()

    except Exception as exc:
        db.session.rollback()
