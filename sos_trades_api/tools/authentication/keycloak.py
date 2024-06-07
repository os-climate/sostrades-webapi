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

import os

from keycloak import KeycloakOpenID

from sos_trades_api.models.database_models import User
from sos_trades_api.server.base_server import app


def get_keycloak_openid():
    KEYCLOAK_SERVER_URL = os.getenv(
        "KEYCLOAK_SERVER_URL", "https://keycloak.gpp-sostrades.com/"
    )
    KEYCLOAK_REALM_NAME = os.getenv("KEYCLOAK_REALM_NAME", "osc")
    # client
    KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "revision")
    KEYCLOAK_CLIENT_SECRET_KEY = os.getenv(
        "KEYCLOAK_CLIENT_SECRET_KEY", "Gu9PnXeWu9A3j3hf8vhrfmePBjkUbBpC"
    )

    keycloak_openid = KeycloakOpenID(
        server_url = KEYCLOAK_SERVER_URL,
        realm_name = KEYCLOAK_REALM_NAME,
        client_id = KEYCLOAK_CLIENT_ID,
        client_secret_key = KEYCLOAK_CLIENT_SECRET_KEY,
        verify=False
    )
    return keycloak_openid


class KeycloakAuthenticator:
    keycloak_openid = get_keycloak_openid()
        
    def auth_url(self, redirect_uri):
        return KeycloakAuthenticator.keycloak_openid.auth_url(redirect_uri)

    def token(self, redirect_uri, code):
        return KeycloakAuthenticator.keycloak_openid.token(redirect_uri=redirect_uri, code=code, grant_type='authorization_code', scope='openid')

    def user_info(self, token):
        return KeycloakAuthenticator.keycloak_openid.userinfo(token)

    def logout_url(self, redirect_uri):
        return KeycloakAuthenticator.keycloak_openid.logout_url(redirect_uri)

    def logout(self, token):
        return KeycloakAuthenticator.keycloak_openid.logout(token)
    
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
        created_user.username = userinfo.get('preferred_username')
        created_user.email = userinfo.get('email')

        created_user.account_source = User.IDP_ACCOUNT

        # User first name and lastname are not provided separately on github
        created_user.firstname = userinfo.get('given_name')
        created_user.lastname = userinfo.get('family_name')

        # If user has not set its profile information, then set username as firstname to avoid missing value
        if created_user.firstname is None or len(created_user.firstname) == 0:
            created_user.firstname = created_user.username

        created_user.company = ''
        created_user.department = ''

        return_url = app.config['SOS_TRADES_FRONT_END_DNS']
        return created_user, return_url