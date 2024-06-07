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
from sos_trades_api.models.database_models import AccessRights
from sos_trades_api.server.base_server import db

"""Default Access rights

Revision ID: 039eba317a4e
Revises: e87facea6cda
Create Date: 2021-10-05 17:55:07.102252

"""

# revision identifiers, used by Alembic.
revision = '039eba317a4e'
down_revision = 'e87facea6cda'
branch_labels = None
depends_on = None


def upgrade():
    access_rights = AccessRights.query.all()

    if access_rights is not None and len(access_rights) == 0:
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

    access_rights = AccessRights.query.all()

    if access_rights is not None and len(access_rights) > 0:
        for access_right in access_rights:
            db.session.delete(access_right)
        db.session.commit()
