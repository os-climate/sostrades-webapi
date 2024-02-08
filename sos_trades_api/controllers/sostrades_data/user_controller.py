'''
Copyright 2022 Airbus SAS
Modifications on 2023/10/12-2023/11/03 Copyright 2023 Capgemini

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
from sos_trades_api.controllers.sostrades_data.group_controller import InvalidGroup

"""
mode: python; py-indent-offset: 4; tab-width: 4; coding: utf-8
User Functions
"""
import traceback
from datetime import datetime, timezone
from sos_trades_api.models.database_models import User, UserProfile, Group, GroupAccessUser, AccessRights
from sos_trades_api.tools.smtp.smtp_service import send_right_update_mail, send_password_reset_mail
from sos_trades_api.tools.authentication.password_generator import check_password, InvalidPassword
from sos_trades_api.tools.authentication.password_generator import generate_password
from os.path import dirname, join, exists
from sqlalchemy import or_, and_, func
from sos_trades_api.server.base_server import db, app
from sos_trades_api.controllers.sostrades_data import group_controller
import uuid
from sos_trades_api import __file__ as sos_trades_api_file
from os import makedirs
import errno
from typing import List


class UserError(Exception):
    """Base User Exception"""

    def __init__(self, msg=None):
        message = None
        if msg is not None:
            if isinstance(msg, Exception):
                message = f'the following exception occurs {msg}.\n{traceback.format_exc()}'
            else:
                message = msg

        Exception.__init__(self, message)

    def __str__(self):
        return self.__class__.__name__ + '(' + Exception.__str__(self) + ')'


class InvalidUser(UserError):
    """Invalid study"""


def get_user_list() -> List[User]:
    """Ask database to retrieve all users information's
    """
    users_query = User.query.all()

    return users_query


def add_user(firstname, lastname, username, password, email, user_profile_id) -> User:
    """Create a new user in database

    :param firstname: user first name
    :type firstname: str

    :param lastname: user last name
    :type lastname: str

    :param username: unique (database side) identifier for a user
    :type username: str

    :param password: user password
    :type password: str

    :param email: unique (database side) email for a user
    :type email: str

    :param default_group_id: user default group
    :type default_group_id: int

    :param user_profile_id: user profile identifier
    :type user_profile_id: int
    """

    # --
    # Make some check about user creation restriction

    # First check for duplicate unique entries (username and email)
    duplicate_users = User.query.filter(
        or_(User.username == username, User.email == email)).all()

    if len(duplicate_users) > 0:
        app.logger.error(
            f'Failed to add a user with duplicated database entries username {username} or email {email}')
        raise InvalidUser(
            f'A user with the same username or email already exist in database')

    new_user = User()
    new_user.firstname = firstname
    new_user.lastname = lastname
    new_user.username = username
    new_user.email = email
    new_user.user_profile_id = user_profile_id
    new_user.set_password(password)

    db.session.add(new_user)

    # Default group => all_users
    all_user_group = Group.query.filter_by(name=Group.ALL_USERS_GROUP).first()
    member_right = AccessRights.query.filter_by(access_right=AccessRights.MEMBER).first()

    set_user_access_group(all_user_group.id, new_user.id, member_right.id)

    db.session.commit()

    # Send an email for renewing password to user
    password_link = reset_user_password(new_user.id)

    return new_user, password_link


def update_user(user_id, firstname, lastname, username, email, user_profile_id) -> (bool, bool):
    """Update an existing user in database

    Return information about profile change (first boolean) and mail sent about this change(second boolean)

    :param user_id: user database primary key
    :type user_id: int

    :param firstname: user first name
    :type firstname: str

    :param lastname: user last name
    :type lastname: str

    :param username: unique (database side) identifier for a user
    :type username: str

    :param email: unique (database side) email for a user
    :type email: str

    :param user_profile_id: user profile identifier
    :type user_profile_id: int

    """
    new_profile = False
    mail_send = False

    user_to_update = db.session.query(User).filter(
        User.id == user_id).first()

    if user_to_update is not None:

        # First check for duplicate unique entries (username and email)
        duplicate_users = User.query.filter(
            and_(or_(User.username == username, User.email == email), User.id != user_id)).all()

        if len(duplicate_users) > 0:
            app.logger.error(
                f'Trying to update a user with duplicated database entries username {username} or email {email}')
            raise InvalidUser(
                f'A user with the same username or email already exist in database')

        user_to_update.firstname = firstname
        user_to_update.lastname = lastname
        user_to_update.username = username
        user_to_update.email = email

        old_user_profile = user_to_update.user_profile_id
        user_to_update.user_profile_id = user_profile_id

        try:
            db.session.commit()
            # Sending warning mail if user profile changed
            if old_user_profile != user_profile_id:
                new_profile = True
                profile_name = 'No profile'
                if user_profile_id is not None:
                    profile_name_query = UserProfile.query.filter(
                        UserProfile.id == user_profile_id).first()
                    if profile_name_query is not None:
                        profile_name = profile_name_query.name
                    else:
                        profile_name = 'No profile'

                mail_send = send_right_update_mail(user_to_update, profile_name)

            return new_profile, mail_send

        except Exception as error:
            app.logger.exception(
                f'Updating user {username} raise the following error')
            raise InvalidUser(
                f'Updating user {username} raise the following error : {error}')

        return f' User {username} has been successfully updated in the database'

    app.logger.error(f'User not found in database, requested id {user_id}')
    raise InvalidUser(
        f'User not found in database')


def delete_user(user_id) -> str:
    """Delete an existing user from database

    Return message according to the user deletion

    :param user_id: user database primary key
    :type user_id: int
    """

    user_to_delete = User.query.filter(User.id == user_id).first()

    if user_to_delete is not None:

        # Select group with user in
        query_group = Group.query.join(GroupAccessUser).filter(Group.id == GroupAccessUser.group_id
                                                               ).filter(GroupAccessUser.user_id == user_id
                                                                        ).all()
        group_with_user = []
        for gr in query_group:
            group_with_user.append(gr.id)

        # Select group with user and count members
        query_count_group = db.session.query(func.count(GroupAccessUser.id), GroupAccessUser.group_id
                                             ).filter(GroupAccessUser.group_id == Group.id
                                                      ).filter(Group.id.in_(group_with_user)
                                                               ).group_by(GroupAccessUser.group_id
                                                                          ).all()

        # Remove group where user is alone
        for qcg in query_count_group:
            if qcg[0] == 1:  # User alone in group
                group_controller.delete_group(qcg[1])

        # Removing user from db
        db.session.delete(user_to_delete)
        db.session.commit()

        message = f' User {user_to_delete.username} has been successfully deleted in the database'
        app.logger.info(message)
        return message

    app.logger.error(f'User not found in database, requested id {user_id}')
    raise InvalidUser(
        f'User cannot be found in the database')


def get_user_profile_list() -> List[UserProfile]:
    """Ask database to retrieved different existing user profiles
    """
    user_profiles = UserProfile.query.all()

    return user_profiles


def reset_user_password(user_id):
    """Reset password of an existing user from database

    :param user_id: user database primary key
    :type user_id: int
    """

    # Get user from db
    user = User.query.filter(User.id == user_id).first()

    if user is not None and user.account_source == User.LOCAL_ACCOUNT:

        try:
            # Generate a unique GUID to change the password
            reset_uuid = str(uuid.uuid4())
            user.reset_uuid = reset_uuid

            # Generate reset link
            reset_link = f'{app.config["SOS_TRADES_FRONT_END_DNS"]}/reset-password?token={user.reset_uuid}'
            send_password_reset_mail(user, reset_link)

            db.session.add(user)
            db.session.commit()

            return reset_link
        except Exception as ex:
            db.session.rollback()
            raise ex

    app.logger.error(f'User not found in database, requested id {user_id}')
    raise InvalidUser(
        f'User cannot be found in the database')


def change_user_password(token, password):
    """Change password of an existing user from database

    :param token: user reset uuid token
    :type token: str

    :param password: new user password
    :type password: str
    """

    # Get user from db using token uuid
    user = User.query.filter(User.reset_uuid == token).first()

    if user is not None and user.account_source == User.LOCAL_ACCOUNT:

        try:
            if check_password(password):
                user.set_password(password)
                user.last_password_reset_date = datetime.now().astimezone(timezone.utc).replace(tzinfo=None)
                user.reset_uuid = None

                db.session.add(user)
                db.session.commit()
                app.logger.info(f'Password successfully changed for user {user.username}')
            else:
                raise InvalidPassword()

        except Exception as ex:
            db.session.rollback()
            raise ex
    else:
        app.logger.error(f'Reset token not found in database, token value {token}')
        raise InvalidUser(f'User cannot be found in the database')


def create_test_user_account():
    # Profile => study user
    study_user_profile = UserProfile.query.filter_by(
        name=UserProfile.STUDY_USER).first()
    # Default group => all_users
    all_user_group = Group.query.filter_by(name=Group.ALL_USERS_GROUP).first()
    # group right => member
    member_right = AccessRights.query.filter_by(
        access_right=AccessRights.MEMBER).first()
    if study_user_profile is not None and all_user_group is not None and member_right is not None:
        users = User.query.filter_by(
            username=User.STANDARD_USER_ACCOUNT_NAME).first()

        if users is None:

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
                set_user_access_group(all_user_group.id, user.id, member_right.id)
            except Exception as exc:
                raise exc

            try:
                __set_password_in_secret_path(password, 'standardUserPassword', 'Standard user')
            except Exception as exc:
                db.session.rollback()
                raise exc

            db.session.commit()


def create_standard_user_account(username, email, firstname, lastname):
    # Profile => study user
    study_user_profile = UserProfile.query.filter_by(
        name=UserProfile.STUDY_USER).first()

    # Default group => all_users
    all_user_group = Group.query.filter_by(name=Group.ALL_USERS_GROUP).first()

    # group right => member
    member_right = AccessRights.query.filter_by(
        access_right=AccessRights.MEMBER).first()

    if study_user_profile is not None and all_user_group is not None and member_right is not None:

        usersByName = User.query.filter_by(
            username=username).first()

        usersByEmail = User.query.filter_by(
            email=email).first()

        if usersByName is None and usersByEmail is None:

            try:
                user = User()
                user.username = username
                user.email = email
                user.firstname = firstname
                user.lastname = lastname
                user.account_source = User.LOCAL_ACCOUNT

                user.user_profile_id = study_user_profile.id

                # Autmatically generate a password inforce policy
                password = generate_password(20)

                # Set password to user
                user.set_password(password)

                db.session.add(user)
                db.session.flush()
                set_user_access_group(all_user_group.id, user.id, member_right.id)
            except Exception as exc:
                raise exc

            try:
                __set_password_in_secret_path(password, f'{username}_Password', 'Standard user')
            except Exception as exc:
                db.session.rollback()
                raise exc

            db.session.commit()


def database_create_user_test():
    """Create a new user_test with all necessaries pre-requisite to be able to launch the test e2e
        """

    user_name = app.config['USER_TEST_E2E'].get('USERNAME', None)
    password = app.config['USER_TEST_E2E'].get('PASSWORD', None)
    email = app.config['USER_TEST_E2E'].get('EMAIL', None)

    # Check if the values are present
    if user_name is None:
        raise Exception(f'Environment variable "USERNAME" not found')

    if password is None:
        raise Exception(f'Environment variable "PASSWORD" not found')

    if email is None:
        raise Exception(f'Environment variable "EMAIL" not found')

    # Set Profile
    study_user_profile = UserProfile.query.filter_by(name=UserProfile.STUDY_USER).first()

    # Set Default group
    all_user_group = Group.query.filter_by(name=Group.ALL_USERS_GROUP).first()

    # Retrieve member rights to set it at "all user" group
    member_right = AccessRights.query.filter_by(access_right=AccessRights.MEMBER).first()

    # Retrieve user_test to check if it already exists
    user_test = User.query.filter_by(username=user_name).first()

    if study_user_profile is not None and all_user_group is not None and member_right is not None and user_test is None:

        try:
            user = User()
            user.username = user_name
            user.email = email
            user.firstname = user_name
            user.lastname = user_name
            user.account_source = User.LOCAL_ACCOUNT

            user.user_profile_id = study_user_profile.id

            # Set password to user
            user.set_password(password)

            db.session.add(user)
            db.session.flush()
            set_user_access_group(all_user_group.id, user.id, member_right.id)
        except Exception as exe:
            db.session.rollback()
            raise exe

        db.session.commit()
    else:
        if study_user_profile is None:
            raise Exception(f"{UserProfile.STUDY_USER} not found in database")
        if all_user_group is None:
            raise Exception(f"{Group.ALL_USERS_GROUP} not found in database")
        if member_right is None:
            raise Exception(f"{AccessRights.MEMBER} not found in database")

    # Check if the group e2e_tests already exist
    group_e2e_tests = Group.query.filter_by(name="e2e_tests").first()
    if group_e2e_tests is not None:
        # Retrieve group_access_user for e2e_tests
        user_test = User.query.filter_by(username=user_name).first()
        group_access_user = GroupAccessUser.query.filter_by(group_id=group_e2e_tests.id).filter_by(user_id=user_test.id)
        if group_access_user is not None:
            try:
                # Retrieve member rights to set it at "all user" group
                owner_right = AccessRights.query.filter_by(access_right=AccessRights.OWNER).first()

                # Create new group_access_user
                new_group_access_user = GroupAccessUser()
                new_group_access_user.user_id = user_test.id
                new_group_access_user.group_id = group_e2e_tests.id
                new_group_access_user.right_id = owner_right.id

                db.session.add(new_group_access_user)
                db.session.flush()
            except Exception as exe:
                db.session.rollback()
                raise exe

            db.session.commit()


def reset_local_user_password_by_name(username):
    '''
    Generate and save a new password for the user with the username = USERNAME
    The password is then saved in a file on the local repository
    '''
    user = User.query.filter_by(username=username).first()

    if user is not None:
        try:
            # Automatically generate a password inforce policy
            password = generate_password(20)
            print(f"password generated: {password}")
            # Set password to user
            user.set_password(password)

            db.session.add(user)

        except Exception as exc:
            raise exc

        try:
            __set_password_in_secret_path(password, f'{username}_Password', username)
        except Exception as exc:
            print(f"error while writing in file: {exc.description}")
            db.session.rollback()
            raise exc

        db.session.commit()


def __set_password_in_secret_path(password, file_name, user_name):
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

    secret_filepath = join(secret_path, file_name)
    with open(secret_filepath, 'w') as f:
        f.write(password)
        f.close()
    print(
        f'{user_name} password created, password in {secret_filepath} file, delete it after copying it in a secret store')


def set_user_default_group(group_id, user_id):
    """
        change a default group into user

        :param user_id: user database primary key
        :type user_id: int

        :param group_id: user default group
        :type group_id: int

    """
    user = db.session.query(User).filter(
        User.id == user_id).first()

    # Retrieve that corresponds to the default group
    group = Group.query.filter(Group.id == group_id).first()

    if user is not None:

        if group is not None:

            try:
                user.default_group_id = group_id
                db.session.add(user)
                db.session.commit()

            except Exception as ex:
                db.session.rollback()
                raise ex

        else:
            raise InvalidGroup(f'Group cannot be found in the database')

    else:
        raise InvalidUser(f'User cannot be found in the database')


def set_user_access_group(group_id, user_id, right_id):
    """
            Set a group access to a user

            :param group_id: group identifier
            :type group_id: int

            :param user_id: user identifier
            :type user_id: int

            :param right_id: access_right identifier
            :type right_id: int

        """
    try:
        user_access_group = GroupAccessUser()
        user_access_group.group_id = group_id
        user_access_group.user_id = user_id
        user_access_group.right_id = right_id
        db.session.add(user_access_group)
    except Exception as exc:
        db.session.rollback()
        raise exc
