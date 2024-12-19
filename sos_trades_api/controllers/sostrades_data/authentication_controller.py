'''
Copyright 2022 Airbus SAS

Modifications on 29/04/2024 Copyright 2024 Capgemini
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

from flask_jwt_extended import create_access_token, create_refresh_token

from sos_trades_api.config import Config
from sos_trades_api.controllers.sostrades_data.group_controller import (
    add_group_access_user_member,
    remove_group_access_user,
)
from sos_trades_api.models.database_models import Group, User
from sos_trades_api.server.base_server import app, db
from sos_trades_api.tools.authentication.authentication import (
    AuthenticationError,
    InvalidCredentials,
    PasswordResetRequested,
    get_authenticated_user,
    manage_user,
)
from sos_trades_api.tools.authentication.github import GitHubSettings
from sos_trades_api.tools.authentication.keycloak import KeycloakAuthenticator
from sos_trades_api.tools.authentication.ldap import LDAPException, check_credentials
from sos_trades_api.tools.authentication.saml import (
    SamlAuthenticationError,
    manage_saml_assertion,
)
from sos_trades_api.tools.smtp.smtp_service import send_new_user_mail

"""
Authentication Functions
"""


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

    if app.config["CREATE_STANDARD_USER_ACCOUNT"] is True:
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
                        "User login or password is incorrect")
        else:
            # Check credential using LDAP request
            user = check_credentials(username, password)
    except LDAPException as ex:
        app.logger.exception(
            f"{username} login or password is incorrect (with LDAP)")
        raise InvalidCredentials(
            "User login or password is incorrect")

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
            mail_send,
        )

    app.logger.error(
        f'"{username}" login or password is incorrect (with LDAP)')
    raise InvalidCredentials(
        "User login or password is incorrect")


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
        app.logger.exception("Authentication exception with saml assertion")
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
            user,
        )

    app.logger.error("User login or password is incorrect (in saml assertion)")
    raise InvalidCredentials(
        "User login or password is incorrect")


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
            user,
        )

    app.logger.error("User login or password is incorrect (in github assertion)")
    raise InvalidCredentials(
        "User login or password is incorrect")



def authenticate_user_keycloak(userinfo: dict):
    """
    Authenticate a user in the platform using Keycloak
    :param userinfo: Response from Keycloak userinfo API
    :type userinfo: dict

    :return: tuple (access_token, refresh_token, url to redirect authentication, user)
    """
    if userinfo:

        keycloak_user, return_url, group_list_associated = KeycloakAuthenticator.create_user_from_userinfo(userinfo)
        user, is_new_user = manage_user(keycloak_user, app.logger)
        if len(group_list_associated) > 0:
            # Get the list of Keycloak groups from the configuration
            config = Config()
            groups_keycloak_from_config = config.keycloak_group_list

            # Convert lists to sets for more efficient operations
            group_set_associated = set(group_list_associated)
            group_set_keycloak = set(groups_keycloak_from_config)

            # Groups to remove access (not associated but in keycloak)
            groups_delete_access_not_associated = group_set_associated - group_set_keycloak
            # Groups to remove access (associated but not in keycloak)
            groups_delete_access_not_in_keycloak = group_set_keycloak - group_set_associated

            # List of all groups to remove access
            all_different_groups = list(groups_delete_access_not_associated.union(groups_delete_access_not_in_keycloak))

            # Remove user access for groups no longer associated
            if all_different_groups:
                for group in all_different_groups:
                    # Find the group object in the database
                    group_to_remove_access = Group.query.filter(Group.name == group).first()

                    # Remove user's access to this group
                    remove_group_access_user(user.id, group_to_remove_access)

            # Identify groups that need to have their access added
            groups_to_add_access = group_set_associated & group_set_keycloak

            # Process each group in the associated list
            if groups_to_add_access:
                for group_name in groups_to_add_access:
                    # Check if the group already exists in the database
                    group = Group.query.filter(Group.name == group_name).first()

                    # If the group doesn't exist, create it
                    if group is None:
                        try:
                            # Initialize a new Group object
                            group = Group()
                            group.name = group_name
                            group.description = group_name
                            group.confidential = False

                            # Add the new group to the database
                            db.session.add(group)
                            db.session.commit()
                        except Exception as ex:
                            # If an error occurs, rollback the session and raise an exception
                            db.session.rollback()
                            raise Exception(f"Error adding group from Keycloak to database: {ex}")

                    # Add or ensure the user has member access to this group
                    add_group_access_user_member(user.id, group)

            else:
                app.logger.warn(f'There is no common groups between "KEYCLOAK_GROUP_LIST" configuration and groups from keycloak of "{user.username}"')
        else:
            app.logger.info("There is any groups from keycloak")


        if is_new_user:
            send_new_user_mail(user)

        # Placeholder: Créez un jeton d'accès et un jeton de rafraîchissement
        access_token = create_access_token(identity=user.email)
        refresh_token = create_refresh_token(identity=user.email)

        app.logger.info(f'"{user.username}" successfully logged (with Keycloak/OpenID)')

        return (
            access_token,
            refresh_token,
            return_url,
            user,
        )

    app.logger.error("User login or password is incorrect (in Keycloak assertion)")
    raise InvalidCredentials(
        "User login or password is incorrect")

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
    """
    Check if all LDAP configuration settings has been set

    :return: boolean, LDAP setting fully available
    """
    data_missing = not app.config["LDAP_SERVER"] or \
        not app.config["LDAP_BASE_DN"] or \
        not app.config["LDAP_FILTER"] or \
        not app.config["LDAP_USERNAME"]

    return not data_missing
