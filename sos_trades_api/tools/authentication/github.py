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
GitHub integration to authenticate user using OAuth
"""

from sos_trades_api.tools.authentication.password_generator import generate_password
from os import environ, path
from datetime import datetime
import json

from sos_trades_api.models.database_models import User, OAuthState
from sos_trades_api.server.base_server import app, db

# GITHUB API KEYS
GITHUB_LOGIN_KEY = 'login'
GITHUB_NAME_KEY = 'name'
GITHUB_MAIL_KEY = 'email'
GITHUB_COMPANY_KEY = 'company'
GITHUB_PRIMARY_KEY = 'primary'

# GITHUB SETTINGS KEYS
GITHUB_OAUTH_SETTINGS = 'GITHUB_OAUTH_SETTINGS'
GITHUB_AUTH_URL = 'GITHUB_AUTH_URL'
GITHUB_API_URL = 'GITHUB_API_URL'
GITHUB_CLIENT_ID = 'GITHUB_CLIENT_ID'
GITHUB_CLIENT_SECRET = 'GITHUB_CLIENT_SECRET'


class GitHubAuthenticationError(Exception):
    """GitHub Authentication Exception"""

    def __init__(self, msg=None):
        Exception.__init__(self, msg)


class GitHubSettings:
    """
    Store GitHub settings
    """

    def __init__(self):
        """
        Constructor
        """

        self.__authorize_url = ''
        self.__token_url = ''
        self.__api_url_user = ''
        self.__api_url_user_email = ''
        self.__github_client_id = ''
        self.__github_client_secret = ''
        self.__github_oauth_settings = {}

        if environ.get(GITHUB_OAUTH_SETTINGS) is not None:
            github_oauth_settings_file = environ.get(GITHUB_OAUTH_SETTINGS)

            if path.exists(github_oauth_settings_file):
                with open(github_oauth_settings_file) as gsf:
                    self.__github_oauth_settings = json.load(gsf)

            if GITHUB_AUTH_URL in self.__github_oauth_settings:
                self.__authorize_url = f'{self.__github_oauth_settings[GITHUB_AUTH_URL]}authorize'
                self.__token_url = f'{self.__github_oauth_settings[GITHUB_AUTH_URL]}access_token'

            if GITHUB_API_URL in self.__github_oauth_settings:
                self.__api_url_user = f'{self.__github_oauth_settings[GITHUB_API_URL]}user'
                self.__api_url_user_email = f'{self.__github_oauth_settings[GITHUB_API_URL]}user/emails'

            if GITHUB_CLIENT_ID in self.__github_oauth_settings:
                self.__github_client_id = self.__github_oauth_settings[GITHUB_CLIENT_ID]

            if GITHUB_CLIENT_SECRET in self.__github_oauth_settings:
                self.__github_client_secret = self.__github_oauth_settings[GITHUB_CLIENT_SECRET]

    @property
    def is_available(self):
        return GITHUB_AUTH_URL in self.__github_oauth_settings and \
               GITHUB_API_URL in self.__github_oauth_settings and \
               GITHUB_CLIENT_ID in self.__github_oauth_settings and \
               GITHUB_CLIENT_SECRET in self.__github_oauth_settings

    @property
    def authorize_url(self):
        return self.__authorize_url

    @property
    def token_url(self):
        return self.__token_url

    @property
    def api_url_user(self):
        return self.__api_url_user

    @property
    def api_user_user_email(self):
        return self.__api_url_user_email

    @property
    def github_client_id(self):
        return self.__github_client_id

    @property
    def github_client_secret(self):
        return self.__github_client_secret

    @staticmethod
    def get_state():
        """
        Generated a random state, store it into the inner dictionary and return it to the caller
        :return: str
        """
        new_state = OAuthState()
        new_state.is_active = True
        new_state.state = generate_password(64)
        new_state.creation_date = datetime.now()

        db.session.add(new_state)
        db.session.commit()

        return new_state.state

    @staticmethod
    def check_state(state_to_check: str):
        """
        Verify given state according the inner dictionary. Checked state is removed from dictionary once checked
        :param state_to_check: state value to check
        :type state_to_check: str
        :return: bool
        """

        result = False

        database_state = OAuthState.query\
            .filter(OAuthState.state == state_to_check)\
            .filter(OAuthState.is_active == 1)\
            .one()

        if database_state is not None:
            database_state.is_active = False
            database_state.check_date = datetime.now()

            second_between_create_and_check = (database_state.check_date - database_state.creation_date).total_seconds()

            if second_between_create_and_check <= 60:
                result = True
            else:
                result = False
                database_state.is_invalidated = True

            db.session.add(database_state)
            db.session.commit()

        return result

    @staticmethod
    def manage_github_assertion(github_api_user_response, github_api_user_email_response):
        """
        Manage GitHub api responses
        :param github_api_user_response: response to authenticated user api
        :type  github_api_user_response: https://docs.github.com/en/rest/users/users#get-the-authenticated-user
        :param github_api_user_email_response: response to authenticated user email api
        :type github_api_user_email_response: https://docs.github.com/en/rest/users/emails#about-the-emails-api
        :return: tuple User, str
        """

        # Here we can assume that the user is authenticated regarding GitHub/OAuth
        # and can access to the application
        user_infos = User()
        user_infos.username = github_api_user_response[GITHUB_LOGIN_KEY]
        user_infos.account_source = User.IDP_ACCOUNT

        # User first name and lastname are not provided separately on github
        user_infos.firstname = github_api_user_response[GITHUB_NAME_KEY]
        user_infos.lastname = ''

        # If user has not set its profile information, then set username as firstname to avoid missing value
        if user_infos.firstname is None or len(user_infos.firstname) == 0:
            user_infos.firstname = user_infos.username

        # Check if email is visible in user profile
        if github_api_user_response[GITHUB_MAIL_KEY]:
            user_infos.email = github_api_user_response[GITHUB_MAIL_KEY]
        # Otherwise request email api
        else:
            primary_email_object = list(filter(lambda em: em[GITHUB_PRIMARY_KEY] is True, github_api_user_email_response))

            if len(primary_email_object) > 0:
                user_infos.email = primary_email_object[0][GITHUB_MAIL_KEY]

        user_infos.company = github_api_user_response[GITHUB_COMPANY_KEY]
        user_infos.department = ''

        return_url = app.config['SOS_TRADES_FRONT_END_DNS']

        return user_infos, return_url



