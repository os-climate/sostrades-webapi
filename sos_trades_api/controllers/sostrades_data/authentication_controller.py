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
Authentication Functions
"""

from flask_jwt_extended import (
    create_access_token, create_refresh_token
)
from sos_trades_api.base_server import db, app
from sos_trades_api.models.database_models import User
from sos_trades_api.tools.authentication.authentication import PasswordResetRequested
from sos_trades_api.tools.authentication.ldap import check_credentials, LDAPException
from sos_trades_api.tools.authentication.saml import manage_saml_assertion, SamlAuthenticationError
from sos_trades_api.tools.authentication.github import GitHubSettings
from sos_trades_api.tools.smtp.smtp_service import send_new_user_mail
from sos_trades_api.tools.authentication.authentication import InvalidCredentials, AuthenticationError, \
    get_authenticated_user, manage_user


def authenticate_user_standard(username, password):
    """
    Authenticate a user based on LDAP access or SoSTrades database

    :params: username, username account login
    :type: string

    :params: password, username account password
    :type: string

    :return: tuple (access_token, refresh_token, user, mail sending status)
    """

    mail_send = False
    # - Check user credential using airbus AD
    user = None

    # Create the list of non ldap user authentication
    users_list = []

    if app.config['CREATE_STANDARD_USER_ACCOUNT'] is True:
        users_list.append(User.STANDARD_USER_ACCOUNT_NAME)

    try:
        no_ldap = ldap_available() is False
        is_builtin_user = username in users_list

        if no_ldap or is_builtin_user:
            users = User.query.filter_by(username=username)

            if users is not None and users.count() > 0:
                found_user = users.first()

                # Check that user is not on a reset password procedure
                if found_user.reset_uuid is not None:
                    raise PasswordResetRequested()

                if found_user.check_password(password):
                    user = found_user
                else:
                    app.logger.error(
                        f'"{username}" login or password is incorrect (with local database)')
                    raise InvalidCredentials(
                        'User login or password is incorrect')
        else:
            # Check credential using LDAP request
            user = check_credentials(username, password)
    except LDAPException as ex:
        app.logger.exception(
            f'{username} login or password is incorrect (with LDAP)')
        raise InvalidCredentials(
            'User login or password is incorrect')

    if user:

        email = user.email
        user, is_new_user = manage_user(user, app.logger)

        if is_new_user:
            mail_send = send_new_user_mail(user)

        app.logger.info(f'"{username}" successfully logged (with LDAP)')

        return (
            create_access_token(identity=email),
            create_refresh_token(identity=email),
            is_new_user,
            mail_send
        )

    app.logger.error(
        f'"{username}" login or password is incorrect (with LDAP)')
    raise InvalidCredentials(
        'User login or password is incorrect')


def authenticate_user_saml(flask_request):
    """
    Authenticate a user

    :param flask_request: a flask request object containing SAML assertion (SAML api used this request)
    :type flask_request: request

    :return: tuple (access_token, refresh_token, url to redirect authentication)

    """

    try:
        saml_user, return_url = manage_saml_assertion(flask_request)
    except SamlAuthenticationError as ex:
        app.logger.exception('Authentication exception with saml assertion')
        raise AuthenticationError(str(ex))

    if saml_user:

        email = saml_user.email
        user, is_new_user = manage_user(saml_user, app.logger)

        if is_new_user:
            send_new_user_mail(user)

        access_token = create_access_token(identity=email)
        refresh_token = create_refresh_token(identity=email)

        app.logger.info(f'"{user.username}" successfully logged (with SAML)')

        return (
            access_token,
            refresh_token,
            return_url,
            user
        )

    app.logger.error('User login or password is incorrect (in saml assertion)')
    raise InvalidCredentials(
        'User login or password is incorrect')


def authenticate_user_github(github_api_user_response: dict, github_api_user_email_response: dict):
    """
    Authenticate a in the platform
    :param github_api_user_response: response to authenticated user api
    :type  github_api_user_response: https://docs.github.com/en/rest/users/users#get-the-authenticated-user
    :param github_api_user_email_response: response to authenticated user email api
    :type github_api_user_email_response: https://docs.github.com/en/rest/users/emails#about-the-emails-api

    :return: tuple (access_token, refresh_token, url to redirect authentication)
    """

    if github_api_user_response and github_api_user_email_response:

        github_user, return_url = GitHubSettings.manage_github_assertion(github_api_user_response, github_api_user_email_response)

        user, is_new_user = manage_user(github_user, app.logger)

        if is_new_user:
            send_new_user_mail(user)

        access_token = create_access_token(identity=github_user.email)
        refresh_token = create_refresh_token(identity=github_user.email)

        app.logger.info(f'"{user.username}" successfully logged (with GitHub/OAuth)')

        return (
            access_token,
            refresh_token,
            return_url,
            user
        )

    app.logger.error('User login or password is incorrect (in github assertion)')
    raise InvalidCredentials(
        'User login or password is incorrect')


def deauthenticate_user():
    """
    Log user out
    in a real app, set a flag in user database requiring login, or
    implement token revocation scheme
    """
    user = get_authenticated_user()

    user.is_logged = False
    db.session.commit()


def refresh_authentication():
    """
    Refresh authentication, issue new access token
    """
    user = get_authenticated_user()
    return create_access_token(identity=user.email)


def ldap_available():
    """ Check if all LDAP configuration settings has been set

    :return: boolean, LDAP setting fully available
    """

    data_missing = not app.config['LDAP_SERVER'] or \
        not app.config['LDAP_BASE_DN'] or \
        not app.config['LDAP_FILTER'] or \
        not app.config['LDAP_USERNAME']

    return not data_missing
