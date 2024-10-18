'''
Copyright 2022 Airbus SAS
Modifications on 2023/09/14-2023/11/03 Copyright 2023 Capgemini

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
from urllib.parse import urlencode, urlparse

import requests
from flask import abort, make_response, redirect, request, session
from flask.json import jsonify
from furl import furl
from onelogin.saml2.auth import OneLogin_Saml2_Auth

from sos_trades_api.controllers.sostrades_data.authentication_controller import (
    AuthenticationError,
    authenticate_user_github,
    authenticate_user_keycloak,
    authenticate_user_saml,
    authenticate_user_standard,
    deauthenticate_user,
    refresh_authentication,
)
from sos_trades_api.server.base_server import app
from sos_trades_api.tools.authentication.authentication import (
    auth_refresh_required,
    auth_required,
    get_authenticated_user,
)
from sos_trades_api.tools.authentication.github import GitHubSettings
from sos_trades_api.tools.authentication.keycloak import KeycloakAuthenticator

"""
Login/logout APIs
"""

def init_saml_auth(req):
    """
    Initialize a SAML object request using saml configuration file and
    a dictionary with necessary content

        :param request, dictionary with sso request informations

        :return: onelogin saml authentication object instance
    """
    auth = OneLogin_Saml2_Auth(req, custom_base_path=os.environ.get("SAML_V2_METADATA_FOLDER"))
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
        "https": "on" if request.scheme == "https" else "off",
        "http_host": request.host,
        "server_port": url_data.port,
        "script_name": request.path,
        "get_data": request.args.copy(),
        "post_data": request.form.copy(),
        "query_string": request.query_string,
    }


@app.route("/api/data/saml/acs", methods=["POST"])
def saml_acs():
    """
    one login assertion consumer service based on SAML V2 protocol
    """
    app.logger.info("SAML authentication requested")
    access_token, refresh_token, return_url, user = authenticate_user_saml(
        request)

    query_parameters = {"token": f"{access_token}###{refresh_token}"}

    url = f"{return_url}/saml?{urlencode(query_parameters)}"

    app.logger.info(f"SAML authentication access granted to {user.email}")

    if "Redirect" in request.form and request.form["Redirect"] == "False":
        data = {"Redirect_url": url}
        return make_response(jsonify(data), 200)
    else:
        return redirect(url)


@app.route("/api/data/saml/sso", methods=["GET"])
def saml_sso():
    """
    sso redirection for user login
    """
    sso_built_url = ""

    try:
        if os.environ.get("SAML_V2_METADATA_FOLDER") is not None:

            # Check that the settings.json file is present:
            sso_path = os.environ["SAML_V2_METADATA_FOLDER"]
            if os.path.exists(sso_path):
                req = prepare_flask_request(request)
                auth = init_saml_auth(req)

                if len(app.config["SOS_TRADES_K8S_DNS"]) > 0:
                    sso_built_url = auth.login(
                        return_to=f'{app.config["SOS_TRADES_K8S_DNS"]}')
                    session["AuthNRequestID"] = auth.get_last_request_id()
    except Exception as ex:
        app.logger.exception("The following error occurs when trying to log using SSO")
        sso_built_url = ""

    return make_response(jsonify(sso_built_url), 200)


@app.route("/api/data/saml/metadata/", methods=["GET"])
def saml_metadata():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    settings = auth.get_settings()
    metadata = settings.get_sp_metadata()
    errors = settings.validate_metadata(metadata)

    if len(errors) == 0:
        resp = make_response(metadata, 200)
        resp.headers["Content-Type"] = "text/xml"
    else:
        resp = make_response(", ".join(errors), 500)
    return resp


@app.route("/api/data/auth/login", methods=["POST"])
def login_api():
    """
    Login user
    """
    try:
        username = request.json.get("username", None)
        password = request.json.get("password", None)

        app.logger.info(f"Standard authentication requested by {username}")

        access_token, refresh_token, new_user, mail_send = authenticate_user_standard(
            username, password)

        app.logger.info(
            f"Standard authentication access granted to {username}")

        return make_response(jsonify({
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "newUser": new_user,
            "mailSend": mail_send,
        }))
    except AuthenticationError as error:
        app.logger.exception(
            f"Standard authentication request failed for {username}")
        abort(403, str(error))


@app.route("/api/data/auth/logout", methods=["POST"])
@auth_refresh_required
def logout_api():
    """
    Log user out
    """
    app.logger.info("User session logout")
    deauthenticate_user()
    return make_response()


@app.route("/api/data/auth/refresh", methods=["POST"])
@auth_refresh_required
def refresh_api():
    """
    Get a fresh access token from a valid refresh token
    """
    try:
        app.logger.info("JWT access token refresh requested")
        access_token = refresh_authentication()

        return make_response(jsonify({
            "accessToken": access_token,
        }))
    except AuthenticationError as error:
        app.logger.exception("JWT access token refresh request failed")
        abort(403, str(error))


@app.route("/api/data/auth/info", methods=["GET"])
@auth_required
def login_info_api():
    """
    Get information about currently logged in user
    """
    try:
        user = get_authenticated_user()
        return make_response(jsonify(user))
    except AuthenticationError as error:
        app.logger.error("authentication error: %s", error)
        abort(403)


@app.route("/api/data/github/oauth/available", methods=["GET"])
def github_oauth_is_available():
    github_settings = GitHubSettings()

    return make_response(jsonify(github_settings.is_available), 200)


@app.route("/api/data/github/oauth/authorize", methods=["GET"])
def github_oauth_authorize():

    github_settings = GitHubSettings()

    github_oauth_url = ""
    if github_settings.is_available:

        params = {
            "client_id": github_settings.github_client_id,
            "scope": "read:user user:email",
            "state": GitHubSettings.get_state(),
            "allow_signup": "true",
        }

        github_oauth_url = furl(github_settings.authorize_url).set(params).url

    return make_response(jsonify(github_oauth_url), 200)


@app.route("/api/data/github/oauth/callback", methods=["GET"])
def github_oauth():

    if "code" not in request.args:
        return jsonify(error="404_no_code"), 404

    if "state" not in request.args:
        return jsonify(error="404_no_state"), 404

    if not GitHubSettings.check_state(request.args["state"]):
        return jsonify(error="404_invalid_state"), 404

    github_settings = GitHubSettings()

    payload = {
        "client_id": github_settings.github_client_id,
        "client_secret": github_settings.github_client_secret,
        "code": request.args["code"],
    }

    headers = {"Accept": "application/json"}
    req = requests.post(github_settings.token_url, params=payload, headers=headers, verify=False)
    resp = req.json()

    if "access_token" not in resp:
        return jsonify(error="404_no_access_token"), 404
    access_token = resp["access_token"]

    headers = {"Authorization": f"token {access_token}"}
    r = requests.get(github_settings.api_url_user, headers=headers, verify=False)
    github_api_user_response = r.json()
    print(github_api_user_response)

    r = requests.get(github_settings.api_user_user_email, headers=headers, verify=False)
    github_api_user_email_response = r.json()
    print(github_api_user_email_response)

    app.logger.info("GitHub/OAuth authentication requested")
    access_token, refresh_token, return_url, user = authenticate_user_github(github_api_user_response,
                                                                             github_api_user_email_response)

    query_parameters = {"token": f"{access_token}###{refresh_token}"}

    url = f"{return_url}/saml?{urlencode(query_parameters)}"

    app.logger.info(f"Github/OAuth authentication access granted to {user.email}")

    return redirect(url)


@app.route("/api/data/keycloak/oauth/authenticate", methods=["GET"])
def authenticate_with_keycloak():

    keycloak_settings = KeycloakAuthenticator()

    auth_url = keycloak_settings.auth_url()

    return make_response(jsonify(auth_url), 200)

@app.route("/api/data/keycloak/oauth/available", methods=["GET"])
def is_keycloak_available():

    keycloak_settings = KeycloakAuthenticator()

    return make_response(jsonify(keycloak_settings.is_available), 200)



@app.route("/api/data/keycloak/callback", methods=["GET"])
def callback():
    # Callback from Keycloak
    if "code" not in request.args:
        return jsonify(error="404_no_code"), 404

    keycloak = KeycloakAuthenticator()

    code = request.args.get("code")
    token = keycloak.token( code)
    userinfo = keycloak.user_info(token["access_token"])

    access_token, refresh_token, return_url, user = authenticate_user_keycloak(userinfo)

    query_parameters = {"token": f"{access_token}###{refresh_token}"}

    url = f"{return_url}/saml?{urlencode(query_parameters)}"

    app.logger.info(f"Github/OAuth authentication access granted to {user.email}")

    return redirect(url)

@app.route("/api/data/keycloak/oauth/logout-url", methods=["GET"])
def logout_url():
    keycloak = KeycloakAuthenticator()
    
    return make_response(jsonify(keycloak.logout_url()), 200)
