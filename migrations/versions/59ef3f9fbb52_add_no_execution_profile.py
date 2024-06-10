"""
add_no_execution_profile

Revision ID: 59ef3f9fbb52
Revises: 6fde15c1f0d5
Create Date: 2023-12-01 16:43:23.266590

"""
from sos_trades_api.models.database_models import UserProfile
from sos_trades_api.server.base_server import db

# revision identifiers, used by Alembic.
revision = "59ef3f9fbb52"
down_revision = "6fde15c1f0d5"
branch_labels = None
depends_on = None


def upgrade():
    study_profile = UserProfile()
    study_profile.name = UserProfile.STUDY_USER_NO_EXECUTION
    study_profile.description = "Study user with no execution rights (platform access rights) account for SoSTrades application"
    db.session.add(study_profile)
    db.session.commit()


def downgrade():
    user_profile = UserProfile.query.filter(
            UserProfile.name == UserProfile.STUDY_USER_NO_EXECUTION).first()

    if user_profile is not None:
        db.session.delete(user_profile)
        db.session.commit()

