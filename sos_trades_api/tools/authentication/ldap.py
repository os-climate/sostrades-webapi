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
LDAP integration to authenticate user on Airbus corp network
"""

import ldap
from sos_trades_api.models.database_models import User
from sos_trades_api.server.base_server import app


class LDAPException(Exception):
    """Base authentication exception"""

    def __init__(self, msg=None):

        Exception.__init__(self, msg)


LDAP_USER_NAME = "userName"
LDAP_UPN = 'userPrincipalName'
LDAP_CN = 'cn'
LDAP_MAIL = 'mail'
LDAP_GIVEN_NAME = 'givenName'
LDAP_SN = 'sn'
LDAP_DISPLAY_NAME = 'displayName'
LDAP_DEPARTMENT = 'department'
LDAP_COMPANY = 'company'


def check_credentials(username, password):
    """Verifies credentials for username and password.
    Returns user information on success or a describing exception in case of faillure

    """

    # ---- LDAP properties
    # - Request
    ldap_filter = app.config['LDAP_FILTER'] % username

    # - Attributes you want to receive for the user
    attrs = [LDAP_UPN, LDAP_CN, LDAP_MAIL,
             LDAP_GIVEN_NAME, LDAP_SN, LDAP_DISPLAY_NAME, LDAP_DEPARTMENT, LDAP_COMPANY]

    # - Fully qualified AD user name
    LDAP_USERNAME = app.config['LDAP_USERNAME'] % username
    # - Password
    LDAP_PASSWORD = password

    try:
        # - Create client ldap object
        ldap_client = ldap.initialize(app.config['LDAP_SERVER'])

        # - Perform a synchronous bind
        ldap_client.set_option(ldap.OPT_REFERRALS, 0)

        # - Execute the request
        ldap_client.simple_bind_s(LDAP_USERNAME, LDAP_PASSWORD)
    except ldap.INVALID_CREDENTIALS:
        ldap_client.unbind()
        raise LDAPException('Wrong username or password')
    except ldap.SERVER_DOWN:
        raise LDAPException(
            f'AD server not available.\nContact your administrator at {app.config["SMTP_SOS_TRADES_ADDR"]}')

    # -  Make the request
    result = ldap_client.search_s(
        app.config['LDAP_BASE_DN'], ldap.SCOPE_SUBTREE, ldap_filter, attrs)

    # result is a list [(dn, {attrs})]
    user_infos = User()
    user_infos.username = username
    user_infos.firstname = 'n/a'
    user_infos.lastname = 'n/a'
    user_infos.email = 'n/a'
    user_infos.department = 'n/a'
    user_infos.company = 'n/a'
    user_infos.account_source = User.IDP_ACCOUNT

    try:
        if LDAP_GIVEN_NAME in result[0][1]:
            user_infos.firstname = result[0][1][LDAP_GIVEN_NAME][0].decode()

        if LDAP_SN in result[0][1]:
            user_infos.lastname = result[0][1][LDAP_SN][0].decode()

        if LDAP_MAIL in result[0][1]:
            user_infos.email = result[0][1][LDAP_MAIL][0].decode()

        if LDAP_DEPARTMENT in result[0][1]:
            user_infos.department = result[0][1][LDAP_DEPARTMENT][0].decode()

        if LDAP_COMPANY in result[0][1]:
            user_infos.company = result[0][1][LDAP_COMPANY][0].decode()
    except Exception as error:
        print(f'LDAP exception attribute : {error}')

    ldap_client.unbind()
    return user_infos
