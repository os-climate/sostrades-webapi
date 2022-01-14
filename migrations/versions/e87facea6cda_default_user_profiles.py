"""Default user profiles

Revision ID: e87facea6cda
Revises: 40ca717b5c0a
Create Date: 2021-10-05 17:52:36.266661

"""
from alembic import op
import sqlalchemy as sa
from sos_trades_api.base_server import db
from sos_trades_api.models.database_models import UserProfile


# revision identifiers, used by Alembic.
revision = 'e87facea6cda'
down_revision = '40ca717b5c0a'
branch_labels = None
depends_on = None

def upgrade():
    userProfiles = UserProfile.query.all()

    if userProfiles is not None and len(userProfiles) == 0:
        admin_profile = UserProfile()
        admin_profile.name = UserProfile.ADMIN_PROFILE
        admin_profile.description = 'Administrator account to manage SoSTrades application'
        db.session.add(admin_profile)

        study_manager_profile = UserProfile()
        study_manager_profile.name = UserProfile.STUDY_MANAGER
        study_manager_profile.description = 'Study manager (manager rights on study) account for SoSTrades application'
        db.session.add(study_manager_profile)

        study_user_profile = UserProfile()
        study_user_profile.name = UserProfile.STUDY_USER
        study_user_profile.description = 'Study user (basic rights) account for SoSTrades application'
        db.session.add(study_user_profile)

        db.session.commit()


def downgrade():
    userProfiles = UserProfile.query.all()

    if userProfiles is not None and len(userProfiles) > 0:

        for userProfile in userProfiles:
            db.session.delete(userProfile)
        db.session.commit()
