"""Default Access rights

Revision ID: 039eba317a4e
Revises: b4c65e383551
Create Date: 2021-10-05 17:55:07.102252

"""
from alembic import op
import sqlalchemy as sa
from sos_trades_api.models.database_models import AccessRights
from sos_trades_api.base_server import db


# revision identifiers, used by Alembic.
revision = '039eba317a4e'
down_revision = 'b4c65e383551'
branch_labels = None
depends_on = None


def upgrade():
    accessRights = AccessRights.query.all()

    if accessRights is not None and len(accessRights) == 0:
        manager_right = AccessRights()
        manager_right.access_right = AccessRights.MANAGER
        manager_right.description = 'Access right manager'
        db.session.add(manager_right)

        contributor_right = AccessRights()
        contributor_right.access_right = AccessRights.CONTRIBUTOR
        contributor_right.description = 'Access right contributor'
        db.session.add(contributor_right)

        commenter_right = AccessRights()
        commenter_right.access_right = AccessRights.COMMENTER
        commenter_right.description = 'Access right commenter'
        db.session.add(commenter_right)

        restricted_viewer_right = AccessRights()
        restricted_viewer_right.access_right = AccessRights.RESTRICTED_VIEWER
        restricted_viewer_right.description = 'Access right restricted viewer'
        db.session.add(restricted_viewer_right)

        member_right = AccessRights()
        member_right.access_right = AccessRights.MEMBER
        member_right.description = 'Access right member'
        db.session.add(member_right)

        owner_right = AccessRights()
        owner_right.access_right = AccessRights.OWNER
        owner_right.description = 'Access right owner'
        db.session.add(owner_right)

        remove_right = AccessRights()
        remove_right.access_right = AccessRights.REMOVE
        remove_right.description = 'Access right remove'
        db.session.add(remove_right)

        db.session.commit()


def downgrade():

    accessRights = AccessRights.query.all()

    if accessRights is not None and len(accessRights) > 0:
        for accessRight in accessRights:
            db.session.delete(accessRight)
        db.session.commit()
