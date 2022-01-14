"""Default Groups

Revision ID: b4c65e383551
Revises: a499f2a1fc01
Create Date: 2021-10-05 17:54:14.072536

"""
from alembic import op
import sqlalchemy as sa
from sos_trades_api.models.database_models import Group, User, GroupAccessUser, AccessRights
from sos_trades_api.base_server import app, db


# revision identifiers, used by Alembic.
revision = 'b4c65e383551'
down_revision = 'a499f2a1fc01'
branch_labels = None
depends_on = None


def upgrade():
    try:
        # Retrieve administrator applicative account
        administrator_applicative_account = User.query.filter(
            User.username == User.APPLICATIVE_ACCOUNT_NAME).first()

        if administrator_applicative_account is None:
            raise ValueError(
                'No administrative account found in database, cannot apply revision')

        # Create 'All users' group
        all_users_group = Group()
        all_users_group.name = Group.ALL_USERS_GROUP
        all_users_group.description = Group.ALL_USERS_GROUP_DESCRIPTION
        all_users_group.creator_id = administrator_applicative_account.id
        all_users_group.confidential = False
        db.session.add(all_users_group)

        # Create 'SosTradesDev' group
        sos_trades_group = Group()
        sos_trades_group.name = app.config['DEFAULT_GROUP_MANAGER_ACCOUNT']
        sos_trades_group.description = Group.SOS_TRADES_DEV_GROUP_DESCRIPTION
        sos_trades_group.creator_id = administrator_applicative_account.id
        sos_trades_group.confidential = False
        db.session.add(sos_trades_group)

        db.session.commit()
    except:
        db.session.rollback()


def downgrade():
    # Check if 'All users' group exist, if not nothing will be done
    all_users_group = Group.query.filter(
        Group.name == Group.ALL_USERS_GROUP).first()

    if all_users_group is not None:
        # Next remove all related right
        GroupAccessUser.query.filter(
            GroupAccessUser.group_id == all_users_group.id).delete()

    db.session.delete(all_users_group)

    # Check if 'SoSTrades_Dev' group exist, if not nothing will be done
    sos_trades_group = Group.query.filter(
        Group.name == app.config['DEFAULT_GROUP_MANAGER_ACCOUNT']).first()

    if sos_trades_group is not None:
        # Next remove all related right
        GroupAccessUser.query.filter(
            GroupAccessUser.group_id == sos_trades_group.id).delete()

    db.session.delete(sos_trades_group)

    db.session.commit()
