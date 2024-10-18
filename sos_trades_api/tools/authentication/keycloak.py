'''
Copyright 2024 Capgemini SAS

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


import json
import os

from keycloak import KeycloakOpenID

from sos_trades_api.models.database_models import User, UserProfile
from sos_trades_api.server.base_server import app

"""
Keycloak integration to authenticate user using OAuth
"""
# KEYCLOAK SETTINGS KEYS
KEYCLOAK_OAUTH_SETTINGS = "KEYCLOAK_OAUTH_SETTINGS"
KEYCLOAK_AUTH_URL = "KEYCLOAK_AUTH_URL"
KEYCLOAK_REDIRECT_URL = "KEYCLOAK_REDIRECT_URL"
KEYCLOAK_REALM_NAME = "KEYCLOAK_REALM_NAME"
KEYCLOAK_CLIENT_ID = "KEYCLOAK_CLIENT_ID"
KEYCLOAK_CLIENT_SECRET = "KEYCLOAK_CLIENT_SECRET"
# url of logout, format with keycloak server url, realm, client id, front url 
KEYCLOAK_LOGOUT_URL = "{}/realms/{}/protocol/openid-connect/logout?client_id={}&post_logout_redirect_uri={}"


class KeycloakAuthenticator:

    def __init__(self):
        """
        Constructor
        """
        keycloak_server_url = ""
        self.keycloak_redirect_url = ""
        keycloak_realm_name = ""
        keycloak_client_id = ""
        keycloak_client_secret = ""
        self.__keycloak_oauth_settings = {}
        
        

        if os.environ.get(KEYCLOAK_OAUTH_SETTINGS) is not None:
            keycloak_oauth_settings_file = os.environ.get(KEYCLOAK_OAUTH_SETTINGS)

            if os.path.exists(keycloak_oauth_settings_file):
                with open(keycloak_oauth_settings_file) as gsf:
                    self.__keycloak_oauth_settings = json.load(gsf)

            if KEYCLOAK_REDIRECT_URL in self.__keycloak_oauth_settings:
                self.keycloak_redirect_url = f"{self.__keycloak_oauth_settings[KEYCLOAK_REDIRECT_URL]}"

            if KEYCLOAK_AUTH_URL in self.__keycloak_oauth_settings:
                keycloak_server_url = f"{self.__keycloak_oauth_settings[KEYCLOAK_AUTH_URL]}"

            if KEYCLOAK_REALM_NAME in self.__keycloak_oauth_settings:
                keycloak_realm_name = f"{self.__keycloak_oauth_settings[KEYCLOAK_REALM_NAME]}"

            if KEYCLOAK_CLIENT_ID in self.__keycloak_oauth_settings:
                keycloak_client_id = self.__keycloak_oauth_settings[KEYCLOAK_CLIENT_ID]

            if KEYCLOAK_CLIENT_SECRET in self.__keycloak_oauth_settings:
                keycloak_client_secret = self.__keycloak_oauth_settings[KEYCLOAK_CLIENT_SECRET]

            self.keycloak_openid = KeycloakOpenID(
                server_url = keycloak_server_url,
                realm_name = keycloak_realm_name,
                client_id = keycloak_client_id,
                client_secret_key = keycloak_client_secret,
                verify=False,
            )

    @property
    def is_available(self):
        return KEYCLOAK_AUTH_URL in self.__keycloak_oauth_settings and \
               KEYCLOAK_REDIRECT_URL in self.__keycloak_oauth_settings and \
               KEYCLOAK_REALM_NAME in self.__keycloak_oauth_settings and \
               KEYCLOAK_CLIENT_ID in self.__keycloak_oauth_settings and \
               KEYCLOAK_CLIENT_SECRET in self.__keycloak_oauth_settings

    def auth_url(self):
        return self.keycloak_openid.auth_url(self.keycloak_redirect_url)

    def token(self, code):
        return self.keycloak_openid.token(redirect_uri=self.keycloak_redirect_url, code=code, grant_type="authorization_code", scope="openid")

    def user_info(self, token):
        return self.keycloak_openid.userinfo(token)

    def logout_url(self):
        return KEYCLOAK_LOGOUT_URL.format(
            self.__keycloak_oauth_settings[KEYCLOAK_AUTH_URL],
            self.__keycloak_oauth_settings[KEYCLOAK_REALM_NAME],
            self.__keycloak_oauth_settings[KEYCLOAK_CLIENT_ID],
            app.config["SOS_TRADES_FRONT_END_DNS"])

    @staticmethod
    def create_user_from_userinfo(userinfo:dict):
        """
        Manage Keycloak api responses
        :param userinfo: response to authenticated user api
        :type userinfo: dict
        :return: tuple User, str
        """
        # Here we can assume that the user is authenticated regarding GitHub/OAuth
        # and can access to the application
        created_user = User()
        created_user.username = userinfo.get("preferred_username")
        created_user.email = userinfo.get("email")

        created_user.account_source = User.IDP_ACCOUNT

        # User first name and lastname are not provided separately on keycloak
        created_user.firstname = userinfo.get("given_name")
        created_user.lastname = userinfo.get("family_name")

        # If user has not set its profile information, then set username as firstname to avoid missing value
        if created_user.firstname is None or len(created_user.firstname) == 0:
            created_user.firstname = created_user.username

        # check role and assign profile if it exists
        roles = userinfo.get('realm_access',{}).get('roles',[])
        if roles is not None:
            if UserProfile.STUDY_MANAGER in roles:
                manager_profile = UserProfile.query.filter(UserProfile.name == UserProfile.STUDY_MANAGER).first()
                created_user.user_profile_id = manager_profile.id
            elif UserProfile.STUDY_USER in roles:
                user_profile = UserProfile.query.filter(UserProfile.name == UserProfile.STUDY_USER).first()
                created_user.user_profile_id = user_profile.id
            elif UserProfile.STUDY_USER_NO_EXECUTION in roles:
                user_profile = UserProfile.query.filter(UserProfile.name == UserProfile.STUDY_USER_NO_EXECUTION).first()
                created_user.user_profile_id = user_profile.id

        created_user.company = ""
        created_user.department = ""

        return_url = app.config["SOS_TRADES_FRONT_END_DNS"]
        return created_user, return_url
