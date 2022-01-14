'''
Copyright 2022 Airbus SAS

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
"""
mode: python; py-indent-offset: 4; tab-width: 4; coding: utf-8
User Functions
"""
import traceback
from datetime import datetime, timezone
from sos_trades_api.models.database_models import User, UserProfile, Group, GroupAccessUser, StudyCase
from sos_trades_api.tools.smtp.smtp_service import send_right_update_mail, send_password_reset_mail
from sos_trades_api.tools.authentication.password_generator import check_password, InvalidPassword
from sos_trades_api.tools.right_management.access_right import is_user_admin
from sqlalchemy import or_, and_, func
from sos_trades_api.base_server import db, app
from sos_trades_api.config import Config
from os.path import join
from sos_trades_api.config import Config
from sos_trades_api.controllers.sostrades_data import group_controller
import shutil
import uuid


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


def get_user_list():
    """
    Ask database to retrieve all users informations

    List is filtered to not retrieve applicative administration account

    :returns: sos_trades_api.models.database_models.User[]
    """
    users_query = User.query.filter(
        User.username != User.APPLICATIVE_ACCOUNT_NAME).all()

    return users_query


def add_user(firstname, lastname, username, password, email, user_profile_id):
    """
    Create a new user in database

    :params: firstname, user first name
    :type: string

    :params: lastname, user last name
    :type: string

    :params: username, unique (database side) identifier for a user
    :type: string

    :params: password, user password
    :type: string

    :params: email, unique (database side) email for a user
    :type: string

    :params: user_profile_id, user profile identifier (some restriction are applied  concerning applicative administrator profile)
    :type: integer

    :return: sos_trades_webapi.models.database_models.User
    """

    # --
    # Make some check abour user creation restriction

    # First check for duplicate unique entries (username and email)
    duplicate_users = User.query.filter(
        or_(User.username == username, User.email == email)).all()

    if len(duplicate_users) > 0:
        app.logger.error(
            f'Failed to add a user with duplicated database entries username {username} or email {email}')
        raise InvalidUser(
            f'A user with the same username or email already exist in database')

    # Check user profile (APPLICATIVE ADMINISTRATOR) profile cannot be assigned
    applicative_administrator_profile = UserProfile.query.filter(
        UserProfile.name == UserProfile.ADMIN_PROFILE).first()

    if user_profile_id == applicative_administrator_profile.id:
        # Dissallow user creation with this profile but does not information
        # about the true reason
        app.logger.error(
            f'Trying to add a user username {username} / email {email} with applicative administrator profile')
        raise InvalidUser(
            f'User profile identifier "{user_profile_id}" does not exist in database')

    new_user = User()
    new_user.firstname = firstname
    new_user.lastname = lastname
    new_user.username = username
    new_user.email = email
    new_user.user_profile_id = user_profile_id
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    return new_user


def update_user(user_id, firstname, lastname, username, email, user_profile_id):
    """
    Update an existing user in database

    :params: user_id, user database primary key
    :type: integer

    :params: firstname, user first name
    :type: string

    :params: lastname, user last name
    :type: string

    :params: username, unique (database side) identifier for a user
    :type: string

    :params: password, user password
    :type: string

    :params: email, unique (database side) email for a user
    :type: string

    :params: user_profile_id, user profile identifier (some restriction are applied  concerning applicative administrator profile)
    :type: integer

    :return: sos_trades_webapi.models.database_models.User
    """
    new_profile = False
    mail_send = False

    user_to_update = db.session.query(User).filter(
        User.id == user_id).first()

    if user_to_update is not None:

        # Check if user to update is the APPLICATIVE ADMINISTRATOR ACCOUNT
        if user_to_update.username == User.APPLICATIVE_ACCOUNT_NAME:
            # Dissallow user update for administrator applicative account but does not information
            # about the true reason
            app.logger.error(
                f'User not found in database, requested id {user_id}')
            raise InvalidUser(f'User not found in database')

        # First check for duplicate unique entries (username and email)
        duplicate_users = User.query.filter(
            and_(or_(User.username == username, User.email == email), User.id != user_id)).all()

        if len(duplicate_users) > 0:
            app.logger.error(
                f'Trying to update a user with duplicated database entries username {username} or email {email}')
            raise InvalidUser(
                f'A user with the same username or email already exist in database')

        # Check user profile (APPLICATIVE ADMINISTRATOR) profile cannot be
        # assigned
        applicative_administrator_profile = UserProfile.query.filter(
            UserProfile.name == UserProfile.ADMIN_PROFILE).first()

        if applicative_administrator_profile.id == user_profile_id:
            # Dissallow user creation with this profile but does not information
            # about the true reason
            app.logger.error(
                f'Trying to add a user username {username} / email {email} with applicative administrator profile')
            raise InvalidUser(
                f'User profile identifier "{user_profile_id}" does not exist in database')

        user_to_update.firstname = firstname
        user_to_update.lastname = lastname
        user_to_update.username = username
        user_to_update.email = email

        old_user_profile = user_to_update.user_profile_id
        user_to_update.user_profile_id = user_profile_id

        try:
            db.session.commit()
            # Sending warning mail if user profile changed
            if(old_user_profile != user_profile_id):
                new_profile = True
                if user_profile_id is None:
                    profilename = 'No profile'
                else:
                    profile_name_query = UserProfile.query.filter(
                        UserProfile.id == user_profile_id).first()
                    if not profile_name_query is None:
                        profilename = profile_name_query.name
                    else:
                        profilename = 'No profile'

                mail_send = send_right_update_mail(user_to_update, profilename)

            return(new_profile, mail_send)

        except Exception as error:
            app.logger.exception(
                f'Updating user {username} raise the following error')
            raise InvalidUser(
                f'Updating user {username} raise the following error : {error}')

        return f' User {username} has been successfully updated in the database'

    app.logger.error(f'User not found in database, requested id {user_id}')
    raise InvalidUser(
        f'User not found in database')


def delete_user(user_id):
    """
    Delete an existing user from database

    :param user_id, user database primary key
    :type integer
    """
    #get user from db
    user_to_delete = User.query.filter(User.id == user_id).first()

    if user_to_delete is not None:

        # Check if user to update is the APPLICATIVE ADMINISTRATOR ACCOUNT
        if user_to_delete.username == User.APPLICATIVE_ACCOUNT_NAME:
            # Dissallow user update for administrator applicative account but does not information
            # about the true reason
            app.logger.error(
                f'User not found in database, requested id {user_id}')
            raise InvalidUser(f'User not found in database')

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


def get_user_profile_list():
    """
    Ask database to retrieved different existing user profiles

    List is filtered to not retrieve applicative administration profile
    """
    user_profile_query = UserProfile.query.filter(
        UserProfile.name != UserProfile.ADMIN_PROFILE).all()

    return user_profile_query


def reset_user_password(user_id):
    """
       Reset password of an existing user from database

       :param user_id, user database primary key
       :type integer
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
    """
       Change password of an existing user from database

       :param token, user reset uuid token
       :type str

       :param password, new user password
       :type str
    """

    # Get user from db using token uuid
    user = User.query.filter(User.reset_uuid == token).first()

    if user is not None and user.account_source == User.LOCAL_ACCOUNT:

        try:
            # Changing admin password is not allowed using API
            if is_user_admin(user.id):
                app.logger.error(f'Token has been set to Administrator profile account {token}')
                raise InvalidUser(
                    f'User cannot be found in the database')

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
