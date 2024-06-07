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
from sos_trades_api.models.database_models import UserProfile
from sos_trades_api.server.base_server import db

"""Default user profiles

Revision ID: e87facea6cda
Revises: 40ca717b5c0a
Create Date: 2021-10-05 17:52:36.266661

"""
# revision identifiers, used by Alembic.
revision = 'e87facea6cda'
down_revision = '40ca717b5c0a'
branch_labels = None
depends_on = None

def upgrade():
    user_profiles = UserProfile.query.all()

    if user_profiles is not None and len(user_profiles) == 0:

        study_manager_profile = UserProfile()
        study_manager_profile.name = UserProfile.STUDY_MANAGER
        study_manager_profile.description = 'Study manager (platform access rights) account for SoSTrades application'
        db.session.add(study_manager_profile)

        study_user_profile = UserProfile()
        study_user_profile.name = UserProfile.STUDY_USER
        study_user_profile.description = 'Study user (user rights) account for SoSTrades application'
        db.session.add(study_user_profile)

        db.session.commit()


def downgrade():
    user_profiles = UserProfile.query.all()

    if user_profiles is not None and len(user_profiles) > 0:

        for user_profile in user_profiles:
            db.session.delete(user_profile)
        db.session.commit()
