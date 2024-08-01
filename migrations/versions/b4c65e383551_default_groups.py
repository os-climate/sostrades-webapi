from sos_trades_api.models.database_models import Group, GroupAccessUser
from sos_trades_api.server.base_server import db

"""Default Groups

Revision ID: b4c65e383551
Revises: 039eba317a4e
Create Date: 2021-10-05 17:54:14.072536

"""
# revision identifiers, used by Alembic.
revision = "b4c65e383551"
down_revision = "039eba317a4e"
branch_labels = None
depends_on = None


def upgrade():
    try:
        # Create 'All users' group
        all_users_group = Group()
        all_users_group.name = Group.ALL_USERS_GROUP
        all_users_group.description = Group.ALL_USERS_GROUP_DESCRIPTION
        all_users_group.confidential = False
        db.session.add(all_users_group)

        # Create 'SosTradesDev' group
        sos_trades_group = Group()
        sos_trades_group.name = Group.SOS_TRADES_DEV_GROUP
        sos_trades_group.description = Group.SOS_TRADES_DEV_GROUP_DESCRIPTION
        sos_trades_group.confidential = False
        sos_trades_group.is_default_applicative_group = True
        db.session.add(sos_trades_group)

        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        raise exc


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
        Group.name == Group.SOS_TRADES_DEV_GROUP).first()

    if sos_trades_group is not None:
        # Next remove all related right
        GroupAccessUser.query.filter(
            GroupAccessUser.group_id == sos_trades_group.id).delete()

    db.session.delete(sos_trades_group)

    db.session.commit()
