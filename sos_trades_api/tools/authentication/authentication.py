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
Authentication tooling function
"""
from datetime import datetime, timezone
from flask_jwt_extended import get_jwt_identity
from functools import wraps
from flask import abort, session
from flask_jwt_extended import verify_jwt_in_request,verify_jwt_refresh_token_in_request
from jwt.exceptions import InvalidSignatureError
from sos_trades_api.base_server import db, app
from sos_trades_api.models.database_models import User, Group, AccessRights, GroupAccessUser, UserProfile
from sos_trades_api.tools.right_management.access_right import has_access_to
from sos_trades_api.tools.right_management import access_right
from werkzeug.exceptions import BadRequest, Unauthorized

class AuthenticationError(Exception):
    """Base Authentication Exception"""

    def __init__(self, msg=None):
        Exception.__init__(self, msg)


class InvalidCredentials(AuthenticationError):
    """Invalid username/password"""


class AccountInactive(AuthenticationError):
    """Account is disabled"""


class AccessDenied(AuthenticationError):
    """Access is denied"""


class UserNotFound(AuthenticationError):
    """User identity not found"""

class PasswordResetRequested(AuthenticationError):
    """User identity not found"""

    def __init__(self):
        super().__init__('Password reset has been requested for this account. Change your password and then log into the application')


def get_authenticated_user():
    """
    Get authentication token user identity and verify account is active
    """
    identity = get_jwt_identity()

    with app.app_context():
        users = User.query.filter_by(email=identity)

        if users is not None and users.count() > 0:
            user = users.first()
            db.session.expunge(user)

            if user.is_logged:
                if user.reset_uuid is not None and user.account_source == User.LOCAL_ACCOUNT:
                    raise PasswordResetRequested()
                else:
                    return user
            else:
                raise AccessDenied(identity)

        raise UserNotFound(identity)


def auth_required(func):
    """
    View decorator - require valid access token
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            user = get_authenticated_user()
            session['user'] = user
            return func(*args, **kwargs)
        except (UserNotFound, AccountInactive, AccessDenied, InvalidSignatureError) as error:
            app.logger.error('authorization failed: %s', error)
            abort(403)
    return wrapper


def study_manager_profile(func):
    """
    View decorator - require valid access token
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:

            if 'user' not in session:
                message = 'Authorization failed: user not authenticated'
                app.logger.error(message)
                raise AccessDenied(message)

            user = session['user']
            if has_access_to(user.user_profile_id, access_right.APP_MODULE_STUDY_MANAGER):
                return func(*args, **kwargs)
            else:
                raise Unauthorized(
                    'You are not allowed to access this resource')
        except (UserNotFound, AccountInactive, AccessDenied, InvalidSignatureError) as error:
            app.logger.error('authorization failed: %s', error)
            abort(403)
    return wrapper


def auth_refresh_required(func):
    """
    View decorator - require valid refresh token
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        verify_jwt_refresh_token_in_request()
        try:
            get_authenticated_user()
            return func(*args, **kwargs)
        except (UserNotFound, AccountInactive, AccessDenied) as error:
            app.logger.error('authorization failed: %s', error)
            abort(403)
    return wrapper


def manage_user(user, logger):
    """
    Method that check the user given as parameter and apply action regarding:
    - if user is existing in database
    - apply some default right regarding user department

    :params: user, user to manager
    :type: sos_trades_api.models.database_models.User

    :params: logger, logger instance to use to log message (this one is given as argument to avoir circular import)
    :type: Logger


    :return: tuple (database user object, new inserted user or not)
    """

    new_user = False

    # - Check if the user is known in database
    users = User.query.filter_by(email=user.email)

    if users is not None and users.count() == 0:

        # In this case the user does not exist in database, by default a new user will be created
        # with a default profile and a default group

        # Retrieve user profile : "Study user"
        study_profile = UserProfile.query.filter(
            UserProfile.name == UserProfile.STUDY_USER).first()

        if study_profile is not None:
            user.user_profile_id = study_profile.id
            db.session.add(user)
        else:
            logger.error(
                f'Default user profile ({UserProfile.STUDY_USER}) not found, user "{user.email}" has not been assigned with a default profile')

        # Retrieve group 'All users'
        all_users_group = Group.query.filter(
            Group.name == Group.ALL_USERS_GROUP).first()

        group_access_user = None
        if all_users_group is not None:

            member_right = AccessRights.query.filter(
                AccessRights.access_right == AccessRights.MEMBER).first()

            if member_right is not None:
                group_access_user = GroupAccessUser()
                group_access_user.group_id = all_users_group.id
                group_access_user.user_id = user.id
                group_access_user.right_id = member_right.id

            else:
                logger.error(
                    f'Default access right ({AccessRights.MEMBER}) not found, user "{user.email}" has not been assigned with a default access right')
        else:
            logger.error(
                f'Default group ({Group.ALL_USERS_GROUP}) not found, user "{user.email}" has not been assigned with a default group')

        # - Add user in database
        new_user = True
        db.session.add(user)

        if group_access_user is not None:
            db.session.add(group_access_user)
            logger.info(
                f'User {user.email} added to database into {Group.ALL_USERS_GROUP} group')

    else:

        temp_department = user.department
        temp_company = user.company
        user = users.first()
        user.department = temp_department
        user.company = temp_company

    user.last_login_date = datetime.now().astimezone(timezone.utc).replace(tzinfo=None)
    user.is_logged = True

    db.session.commit()

    return user, new_user
