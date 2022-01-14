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
SAML integration to authenticate user on Airbus corp network with SSO
"""
import os
import sos_trades_api

from sos_trades_api.base_server import app

from sos_trades_api.models.database_models import User

from urllib.parse import urlparse, urlencode
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.utils import OneLogin_Saml2_Utils


SSO_FIRST_NAME = 'firstName'
SSO_LAST_NAME = 'lastname'
SSO_MAIL = 'mail'
SSO_COMPANY = 'company'
SSO_DEPARTMENT = 'department'


class SamlAuthenticationError(Exception):
    """Saml Authentication Exception"""

    def __init__(self, msg=None):
        Exception.__init__(self, msg)


def init_saml_auth(req):
    """
        :param request, dictionary with sso request informations

        :return: onelogin saml authentication object instance
    """
    auth = OneLogin_Saml2_Auth(req, custom_base_path=os.environ['SAML_V2_METADATA_FOLDER'])
    return auth


def prepare_flask_request(request):
    """
        :param: flask request coming from the SSO IDP

        :return: a new dictionary with key intended by SSO api
    """

    # If server is behind proxys or balancers use the HTTP_X_FORWARDED fields
    url_data = urlparse(request.url)
    return {
        'https': 'on' if request.scheme == 'https' else 'off',
        'http_host': request.host,
        'server_port': url_data.port,
        'script_name': request.path,
        'get_data': request.args.copy(),
        'post_data': request.form.copy(),
        'query_string': request.query_string
    }


def manage_saml_assertion(flask_request):
    """ one login assertion consumer service based on SAML V2 protocol

    :param: flask_request, incoming flask request coming from SSO IDP
    """

    req = prepare_flask_request(flask_request)
    auth = init_saml_auth(req)

    auth.process_response()
    errors = auth.get_errors()

    not_auth_warn = not auth.is_authenticated()
    if len(errors) == 0 and not not_auth_warn:

        # Here we can assume that the user is authenticated regarding SSO
        # and can access to the application
        request_user_attributes = auth.get_attributes()
        request_user_identifier = auth.get_nameid()

        self_url = OneLogin_Saml2_Utils.get_self_url(req)

        user_infos = User()
        user_infos.username = request_user_identifier

        user_infos.firstname = request_user_attributes[SSO_FIRST_NAME]
        user_infos.lastname = request_user_attributes[SSO_LAST_NAME]
        user_infos.email = request_user_attributes[SSO_MAIL]

        if SSO_DEPARTMENT in request_user_attributes:
            user_infos.department = request_user_attributes[SSO_DEPARTMENT]
        else:
            user_infos.department = 'n/a'

        if SSO_COMPANY in request_user_attributes:
            user_infos.company = request_user_attributes[SSO_COMPANY]
        else:
            user_infos.company = 'n/a'

        if 'RelayState' in flask_request.form and self_url != flask_request.form['RelayState']:
            return_url = f'{auth.redirect_to(flask_request.form["RelayState"])}'
        else:
            return_url = f'{auth.redirect_to(app.config["SOS_TRADES_FRONT_END_DNS"])}'

        return user_infos, return_url

    elif auth.get_settings().is_debug_active():
        raise SamlAuthenticationError(auth.get_last_error_reason())
