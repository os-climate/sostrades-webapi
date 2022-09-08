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
from sos_trades_api.tools.right_management.functional.study_case_access_right import StudyCaseAccess

"""
mode: python; py-indent-offset: 4; tab-width: 4; coding: utf-8
Authentication tooling function
"""
from datetime import datetime
import pytz
from flask_jwt_extended import get_jwt_identity
from functools import wraps
from flask import abort, session, request
from flask_jwt_extended import verify_jwt_in_request,verify_jwt_refresh_token_in_request
from jwt.exceptions import InvalidSignatureError
import base64
from sos_trades_api.server.base_server import db, app
from sos_trades_api.models.database_models import User, Group, AccessRights, GroupAccessUser, UserProfile, Device
from sos_trades_api.tools.right_management.access_right import has_access_to
from sos_trades_api.tools.right_management import access_right
from sos_trades_api.tools.right_management.functional.group_access_right import GroupAccess
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


def set_user_from_api_key(authorization):
    """
    Extract api-key information from authorization header
    authorization header has the following form: Bearer base64encodedkey

    Once decoded the key has the following form: <apikey>:<user-identifier>
    :param authorization: bearer with base64 encoded key
    :type authorization: str
    :return: User
    """

    # Checks that Authorization is a Bearer token
    if 'Bearer' not in authorization:
        abort(401, 'Missing Authorization header')

    # Extract token from value and do the base64 decoding
    bearer_token = authorization.replace('Bearer ', '')
    decoded_bearer_token = base64.b64decode(bearer_token).decode('utf-8')

    api_key = ''
    user_identifier = ''

    # User-identifier is optional so check if token contains only key or the key and user
    if ':' not in decoded_bearer_token:
        api_key = decoded_bearer_token
    else:
        split_decoded_bearer_token = decoded_bearer_token.split(':')

        if len(split_decoded_bearer_token) > 2:
            abort(401, 'Missing Authorization header')
        api_key = split_decoded_bearer_token[0]
        user_identifier = split_decoded_bearer_token[1]

    # Check api key validity
    api_key_device = Device.query.filter(Device.device_key == api_key).first()

    if api_key_device is None:
        abort(401, 'Invalid api-key')

    # Get api-key associated group
    api_key_group = Group.query.filter(Group.id == api_key_device.group_id).one()

    if api_key_group is None:
        abort(401, 'Invalid api-key')

    # If user-identifier is not set then get the group owner as user
    # otherwise check the user is member of the group
    user = None
    if user_identifier == '':
        result = db.session.query(User, Group, GroupAccessUser, AccessRights) \
            .filter(User.id == GroupAccessUser.user_id) \
            .filter(Group.id == GroupAccessUser.group_id) \
            .filter(Group.id == api_key_group.id) \
            .filter(GroupAccessUser.right_id == AccessRights.id) \
            .filter(AccessRights.access_right == AccessRights.OWNER).first()

        if result is None:
            abort(403, 'Api-key unauthorized')
        user = result.User
    else:
        user = User.query.filter(User.email == user_identifier).one()
        group = GroupAccess(user.id)
        is_member_of_group = \
            group.check_user_right_for_group(AccessRights.MANAGER, group_id=api_key_group.id) or \
            group.check_user_right_for_group(AccessRights.MEMBER, group_id=api_key_group.id) or \
            group.check_user_right_for_group(AccessRights.OWNER, group_id=api_key_group.id)

        if not is_member_of_group:
            abort(403, 'User unauthorized')

    session['user'] = user
    session['group'] = api_key_group


def api_key_required(func):
    """
    View decorator - require valid api key
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            if request.headers:
                auth_header = request.headers.get('Authorization', None)

                if not auth_header:
                    abort(401, 'Missing Authorization header')
                set_user_from_api_key(auth_header)

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


def manage_user(logged_user, logger):
    """
    Method that check the user given as parameter and apply action regarding:
    - if user is existing in database
    - apply some default right regarding user department

    :params: logged_user, logged user to manage
    :type: sos_trades_api.models.database_models.User

    :params: logger, logger instance to use to log message (this one is given as argument to avoid circular import)
    :type: Logger


    :return: tuple (database user object, new inserted user or not)
    """

    is_new = False
    managed_user = None

    # - Check if the user is known in database
    users = User.query.filter_by(email=logged_user.email)

    if users is not None and users.count() == 0:

        # In this case the user does not exist in database, by default a new user will be created
        # with a default profile and a default group

        managed_user = User()
        managed_user.init_from_user(logged_user)

        # Retrieve user profile : "Study user"
        study_profile = UserProfile.query.filter(
            UserProfile.name == UserProfile.STUDY_USER).first()

        if study_profile is not None:
            managed_user.user_profile_id = study_profile.id
        else:
            logger.error(
                f'Default user profile ({UserProfile.STUDY_USER}) not found, user "{managed_user.email}" has not been assigned with a default profile')

        # User is basically created, so commit in database
        managed_user.last_login_date = datetime.now().astimezone(pytz.UTC)
        managed_user.is_logged = True
        db.session.add(managed_user)
        db.session.flush()

        # Next manage user default group access
        # Retrieve group 'All users'
        all_users_group = Group.query.filter(
            Group.name == Group.ALL_USERS_GROUP).first()

        if all_users_group is not None:

            member_right = AccessRights.query.filter(
                AccessRights.access_right == AccessRights.MEMBER).first()

            if member_right is not None:
                group_access_user = GroupAccessUser()
                group_access_user.group_id = all_users_group.id
                group_access_user.user_id = managed_user.id
                group_access_user.right_id = member_right.id
                db.session.add(group_access_user)
                db.session.commit()
                logger.info(
                    f'User {managed_user.email} added to database into {Group.ALL_USERS_GROUP} group')

            else:
                logger.error(
                    f'Default access right ({AccessRights.MEMBER}) not found, user "{managed_user.email}" has not been assigned with a default access right')
        else:
            logger.error(
                f'Default group ({Group.ALL_USERS_GROUP}) not found, user "{managed_user.email}" has not been assigned with a default group')

        is_new = True

    else:

        temp_department = logged_user.department
        temp_company = logged_user.company
        managed_user = users.first()
        managed_user.department = temp_department
        managed_user.company = temp_company

        # Update user state (and information from previous else block if needed)
        managed_user.last_login_date = datetime.now().astimezone(pytz.UTC)
        managed_user.is_logged = True

        db.session.add(managed_user)
        db.session.commit()

    return managed_user, is_new


def has_user_access_right(access_right):
    """
    View decorator

    Checks that authenticated user has wanted access right

    :param access_right: access right to check
    :type: AccessRights
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):

            if 'user' not in session:
                message = 'Authorization failed: user not authenticated'
                app.logger.error(message)
                raise AccessDenied(message)

            try:
                user = session['user']
                study_id = kwargs.get("study_id")
                if study_id is None:
                    raise KeyError('You must have "study_id" parameter to check access right')

                # Verify user has study case authorisation on study
                study_case_access = StudyCaseAccess(user.id)

                if not study_case_access.check_user_right_for_study(access_right, study_id):
                    raise AccessDenied('You do not have the necessary rights to access this study case')

            except Exception as e:
                abort(403, str(e))

            return func(*args, **kwargs)

        return wrapper

    return decorator

