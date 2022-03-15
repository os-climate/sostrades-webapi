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
from flask import request, jsonify, make_response, session
from werkzeug.exceptions import BadRequest, Unauthorized

from sos_trades_api.base_server import app
from sos_trades_api.tools.authentication.password_generator import generate_password
from sos_trades_api.tools.authentication.authentication import auth_required, get_authenticated_user, study_manager_profile
from sos_trades_api.controllers.sostrades_data.user_controller import add_user, update_user as update_user_controller, \
    get_user_list, get_user_profile_list, delete_user as delete_user_controller, reset_user_password, change_user_password
from sos_trades_api.tools.right_management.access_right import has_access_to
from sos_trades_api.tools.right_management import access_right
from sos_trades_api.models.user_application_right import UserApplicationRight


@app.route(f'/api/data/user', methods=['GET'])
@auth_required
def users():

    resp = make_response(jsonify(get_user_list()), 200)
    return resp


@app.route(f'/api/data/user', methods=['POST'])
@auth_required
@study_manager_profile
def create_user():
    # Proceeding after rights verification
    firstname = request.json.get('firstname', None)
    lastname = request.json.get('lastname', None)
    username = request.json.get('username', None)
    email = request.json.get('email', None)
    user_profile_id = request.json.get('userprofile', None)

    missing_parameter = []
    if firstname is None:
        missing_parameter.append('Missing mandatory parameter: firstname')
    if lastname is None:
        missing_parameter.append('Missing mandatory parameter: lastname')
    if username is None:
        missing_parameter.append('Missing mandatory parameter: username')
    if email is None:
        missing_parameter.append('Missing mandatory parameter: email')
    # User profile is not mandatory

    if len(missing_parameter) > 0:
        raise BadRequest('\n'.join(missing_parameter))

    # Create user with a randomly generated password
    added_user, reset_link = add_user(firstname, lastname, username, generate_password(), email, user_profile_id)

    app.logger.info(f'User {added_user} created')

    resp = make_response(jsonify({
        'user': added_user,
        'password_link': reset_link
    }), 200)

    return resp


@app.route(f'/api/data/user/<int:user_identifier>', methods=['POST'])
@auth_required
@study_manager_profile
def update_user(user_identifier):

    if user_identifier is None or user_identifier <= 0:
        raise BadRequest(f'Invalid argument value for user_identifier.\nReceived {user_identifier}, expected stricly positive integer')

    # Proceeding after rights verification
    user_id_updated = request.json.get('id', None)
    firstname = request.json.get('firstname', None)
    lastname = request.json.get('lastname', None)
    username = request.json.get('username', None)
    email = request.json.get('email', None)
    user_profile_id = request.json.get('userprofile', None)

    missing_parameter = []
    if user_id_updated is None:
        missing_parameter.append(
            'Missing mandatory parameter: id')
    if firstname is None:
        missing_parameter.append('Missing mandatory parameter: firstname')
    if lastname is None:
        missing_parameter.append('Missing mandatory parameter: lastname')
    if username is None:
        missing_parameter.append('Missing mandatory parameter: username')
    if email is None:
        missing_parameter.append('Missing mandatory parameter: email')

    if len(missing_parameter) > 0:
        raise BadRequest('\n'.join(missing_parameter))

    if not user_id_updated == user_identifier:
        raise BadRequest('Invalid payload identifier regard url parameter')

    new_profile, mail_send = update_user_controller(
        user_id_updated, firstname, lastname, username, email, user_profile_id)

    app.logger.info(f'User {user_id_updated} updated')

    resp = make_response(jsonify({
        'newProfile': new_profile,
        'mailSend': mail_send
    }), 200)
    return resp


@app.route(f'/api/data/user', methods=['DELETE'])
@auth_required
@study_manager_profile
def delete_user():

    # Proceeding after rights verification
    user_id = request.json.get('user_id', None)

    if user_id is None:
        raise BadRequest('Missing mandatory parameter: user_id')

    resp = make_response(jsonify(delete_user_controller(user_id)), 200)
    app.logger.info(f'User {user_id} deleted')
    return resp
    
    
@app.route(f'/api/data/user/profile', methods=['GET'])
@auth_required
def user_profiles():
    resp = make_response(jsonify(get_user_profile_list()), 200)
    return resp


@app.route(f'/api/data/user/current-user', methods=['GET'])
@auth_required
def current_user():
    """
    Get information about currently logged in user
    """
    user = session['user']

    # Adding right information
    user_dto = UserApplicationRight(user)
    return make_response(jsonify(user_dto), 200)


@app.route(f'/api/data/user/reset-password', methods=['POST'])
@auth_required
def reset_password():
    """
    tag account to change its password

    Changing password can be done only by:
    - the Administrator
    - the user owner of its account

    Administrator password cannot be reset this way

    """

    user_identifier = request.json.get('user_identifier', None)

    if user_identifier is None:
        raise BadRequest ('Missing mandatory parameter: user_identifier')

    user = session['user']

    can_reset_password = has_access_to(user.user_profile_id, access_right.APP_MODULE_STUDY_MANAGER) or user.id == user_identifier

    if not can_reset_password:
        raise Unauthorized(
            'You are not allowed to access this resource')

    reset_link = reset_user_password(user_identifier)

    return make_response(jsonify(reset_link), 200)


@app.route(f'/api/data/user/change-password', methods=['POST'])
def change_password():
    """
    change password of a user account
    """

    password = request.json.get('password', None)
    token = request.json.get('token', None)

    missing_parameter = []
    if password is None:
        missing_parameter.append(
            'Missing mandatory parameter: password')

    if token is None:
        missing_parameter.append(
            'Missing mandatory parameter: token')

    if len(missing_parameter) > 0:
        raise BadRequest('\n'.join(missing_parameter))

    change_user_password(token, password)

    return make_response(None, 200)
