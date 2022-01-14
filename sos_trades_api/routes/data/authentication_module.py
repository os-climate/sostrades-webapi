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
Login/logout APIs
"""

from flask import request, make_response, abort, session, redirect
from flask.json import jsonify
import os
from sos_trades_api.base_server import app

from sos_trades_api.controllers.sostrades_data.authentication_controller import \
    (authenticate_user_standard, deauthenticate_user, refresh_authentication, AuthenticationError,
     authenticate_user_saml)

from sos_trades_api.tools.authentication.authentication import auth_required, auth_refresh_required, \
    get_authenticated_user
from urllib.parse import urlparse, urlencode
from onelogin.saml2.auth import OneLogin_Saml2_Auth


def init_saml_auth(req):
    """
    Initialize a SAML object request using saml configuration file and
    a dictionary with necessary content

        :param request, dictionary with sso request informations

        :return: onelogin saml authentication object instance
    """
    auth = OneLogin_Saml2_Auth(req, custom_base_path=os.environ.get('SAML_V2_METADATA_FOLDER'))
    return auth


def prepare_flask_request(request):
    """
    Prepare saml data based on the http request content
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


@app.route(f'/api/data/saml/acs', methods=['POST'])
def saml_acs():
    """ one login assertion consumer service based on SAML V2 protocol
    """

    app.logger.info(f'SAML authentication requested')
    access_token, refresh_token, return_url, user = authenticate_user_saml(
        request)

    query_parameters = {'token': f'{access_token}###{refresh_token}'}

    url = f'{return_url}/saml?{urlencode(query_parameters)}'

    app.logger.info(f'SAML authentication access granted to {user.email}')

    if 'Redirect' in request.form and request.form['Redirect'] == 'False':
        data = {'Redirect_url': url}
        return make_response(jsonify(data), 200)
    else:
        return redirect(url)


@app.route(f'/api/data/saml/sso', methods=['GET'])
def saml_sso():
    """ sso redirection for user login
    """

    req = prepare_flask_request(request)
    auth = init_saml_auth(req)

    # If AuthNRequest ID need to be stored in order to later validate it, do
    # instead

    sso_built_url = ''

    if len(app.config["SOS_TRADES_K8S_DNS"]) > 0:
        sso_built_url = auth.login(
            return_to=f'{app.config["SOS_TRADES_K8S_DNS"]}')
        session['AuthNRequestID'] = auth.get_last_request_id()

    return make_response(jsonify(sso_built_url), 200)


@app.route(f'/api/data/saml/metadata/', methods=['GET'])
def saml_metadata():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    settings = auth.get_settings()
    metadata = settings.get_sp_metadata()
    errors = settings.validate_metadata(metadata)

    if len(errors) == 0:
        resp = make_response(metadata, 200)
        resp.headers['Content-Type'] = 'text/xml'
    else:
        resp = make_response(', '.join(errors), 500)
    return resp


@app.route(f'/api/data/auth/login', methods=['POST'])
def login_api():
    """
    Login user
    """
    try:
        username = request.json.get('username', None)
        password = request.json.get('password', None)

        app.logger.info(f'Standard authentication requested by {username}')

        access_token, refresh_token, new_user, mail_send = authenticate_user_standard(
            username, password)

        app.logger.info(
            f'Standard authentication access granted to {username}')

        return make_response(jsonify({
            'accessToken': access_token,
            'refreshToken': refresh_token,
            'newUser': new_user,
            'mailSend': mail_send
        }))
    except AuthenticationError as error:
        app.logger.exception(
            f'Standard authentication request failed for {username}')
        abort(403, str(error))


@app.route(f'/api/data/auth/logout', methods=['POST'])
@auth_refresh_required
def logout_api():
    """
    Log user out
    """
    app.logger.info(f'User session logout')
    deauthenticate_user()
    return make_response()


@app.route(f'/api/data/auth/refresh', methods=['POST'])
@auth_refresh_required
def refresh_api():
    """
    Get a fresh access token from a valid refresh token
    """
    try:
        app.logger.info(f'JWT access token refresh requested')
        access_token = refresh_authentication()
        return make_response(jsonify({
            'accessToken': access_token
        }))
    except AuthenticationError as error:
        app.logger.exception(f'JWT access token refresh request failed')
        abort(403, str(error))


@app.route(f'/api/data/auth/info', methods=['GET'])
@auth_required
def login_info_api():
    """
    Get information about currently logged in user
    """
    try:
        user = get_authenticated_user()
        return make_response(jsonify(user))
    except AuthenticationError as error:
        app.logger.error('authentication error: %s', error)
        abort(403)
