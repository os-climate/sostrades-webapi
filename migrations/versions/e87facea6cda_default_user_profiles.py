"""
Default user profiles

Revision ID: e87facea6cda
Revises: 40ca717b5c0a
Create Date: 2021-10-05 17:52:36.266661

"""
from sos_trades_api.models.database_models import UserProfile
from sos_trades_api.server.base_server import db


# revision identifiers, used by Alembic.
revision = "e87facea6cda"
down_revision = "40ca717b5c0a"
branch_labels = None
depends_on = None

def upgrade():
    user_profiles = UserProfile.query.all()

    if user_profiles is not None and len(user_profiles) == 0:

        study_manager_profile = UserProfile()
        study_manager_profile.name = UserProfile.STUDY_MANAGER
        study_manager_profile.description = "Study manager (platform access rights) account for SoSTrades application"
        db.session.add(study_manager_profile)

        study_user_profile = UserProfile()
        study_user_profile.name = UserProfile.STUDY_USER
        study_user_profile.description = "Study user (user rights) account for SoSTrades application"
        db.session.add(study_user_profile)

        db.session.commit()


def downgrade():
    user_profiles = UserProfile.query.all()

    if user_profiles is not None and len(user_profiles) > 0:

        for user_profile in user_profiles:
            db.session.delete(user_profile)
        db.session.commit()
