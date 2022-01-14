"""Default Standard user

Revision ID: f60bb248ada1
Revises: 039eba317a4e
Create Date: 2021-10-05 17:55:56.359717

"""
from alembic import op
import sqlalchemy as sa
from sos_trades_api import __file__ as sos_trades_api_file
from sos_trades_api.models.database_models import UserProfile, User, Group,\
    AccessRights, GroupAccessUser
from sos_trades_api.base_server import app, db
from sos_trades_api.tools.authentication.password_generator import generate_password
from os.path import dirname, join, exists
from os import makedirs
import errno


# revision identifiers, used by Alembic.
revision = 'f60bb248ada1'
down_revision = '039eba317a4e'
branch_labels = None
depends_on = None


def upgrade():
    # Get all database informations needed to add the user

    # Profile => study user
    study_user_profile = UserProfile.query.filter_by(
        name=UserProfile.STUDY_USER).first()

    # Default group => all_users
    all_user_group = Group.query.filter_by(name=Group.ALL_USERS_GROUP).first()

    # group right => member
    member_right = AccessRights.query.filter_by(
        access_right=AccessRights.MEMBER).first()

    if study_user_profile is not None and all_user_group is not None and member_right is not None:

        if app.config['CREATE_STANDARD_USER_ACCOUNT'] is True:
            users = User.query.filter_by(
                username=User.STANDARD_USER_ACCOUNT_NAME)

            if users is not None and users.count() == 0:
                try:
                    user = User()
                    user.username = User.STANDARD_USER_ACCOUNT_NAME
                    user.email = User.STANDARD_USER_ACCOUNT_EMAIL
                    user.firstname = User.STANDARD_USER_ACCOUNT_NAME
                    user.lastname = ''

                    user.user_profile_id = study_user_profile.id

                    # Autmatically generate a password inforce policy
                    password = generate_password(20)

                    # Set password to user
                    user.set_password(password)

                    db.session.add(user)
                    db.session.flush()

                    user_access_group = GroupAccessUser()
                    user_access_group.group_id = all_user_group.id
                    user_access_group.user_id = user.id
                    user_access_group.right_id = member_right.id
                    db.session.add(user_access_group)

                except Exception as exc:
                    raise exc

                try:
                    # Write password in a file to let platform installer
                    # retrieve it
                    root_folder = dirname(sos_trades_api_file)
                    secret_path = join(root_folder, 'secret')

                    if not exists(secret_path):
                        try:
                            makedirs(secret_path)
                        except OSError as exc:  # Guard against race condition
                            if exc.errno != errno.EEXIST:
                                raise

                    secret_filepath = join(secret_path, 'standardUserPassword')
                    with open(secret_filepath, 'w') as f:
                        f.write(password)
                        f.close()
                    print(
                        f'Standard user account created, password in {secret_filepath} file, delete it after copying it in a secret store')
                except Exception as exc:
                    db.session.rollback()
                    raise exc

                db.session.commit()


def downgrade():
    users = User.query.filter_by(username=User.STANDARD_USER_ACCOUNT_NAME)

    if users is not None and users.count() > 0:
        db.session.delete(users.first())
        db.session.commit()
