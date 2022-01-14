"""Default Applicative account

Revision ID: a499f2a1fc01
Revises: e87facea6cda
Create Date: 2021-10-05 17:53:34.638343

"""
from alembic import op
import sqlalchemy as sa
from sos_trades_api import __file__ as sos_trades_api_file
from sos_trades_api.config import Config
from sos_trades_api.models.database_models import User, UserProfile
from sos_trades_api.base_server import app, db
from sos_trades_api.tools.authentication.password_generator import generate_password
from os.path import dirname, join, exists
from os import makedirs
import errno

# revision identifiers, used by Alembic.
revision = 'a499f2a1fc01'
down_revision = 'e87facea6cda'
branch_labels = None
depends_on = None


def upgrade():
    adminProfile = UserProfile.query.filter_by(
        name=UserProfile.ADMIN_PROFILE).first()

    users = User.query.filter_by(username=User.APPLICATIVE_ACCOUNT_NAME)

    if users is not None and users.count() == 0:
        try:
            user = User()
            user.username = User.APPLICATIVE_ACCOUNT_NAME
            user.firstname = User.APPLICATIVE_ACCOUNT_NAME
            user.lastname = ''
            user.email = User.APPLICATIVE_ACCOUNT_EMAIL
            user.user_profile_id = adminProfile.id

            # Automatically generate a password inforce policy
            password = generate_password(20)

            # Set password to user
            user.set_password(password)

            db.session.add(user)

        except Exception as exc:
            raise exc

        try:
            # Write password in a file to let platform installer retrieve it
            root_folder = dirname(sos_trades_api_file)
            secret_path = join(root_folder, 'secret')

            if not exists(secret_path):
                try:
                    makedirs(secret_path)
                except OSError as exc:  # Guard against race condition
                    if exc.errno != errno.EEXIST:
                        raise

            secret_filepath = join(secret_path, 'adminPassword')
            with open(secret_filepath, 'w') as f:
                f.write(password)
                f.close()
            print(
                f'Administrator account created, password in {secret_filepath} file, delete it after copying it in a secret store')
        except Exception as exc:
            db.session.rollback()
            raise exc

        db.session.commit()


def downgrade():
    users = User.query.filter_by(username=User.APPLICATIVE_ACCOUNT_NAME)

    if users is not None and users.count() > 0:
        user = users.first()
        db.session.delete(user)

    db.session.commit()
