'''
Copyright 2022 Airbus SAS
Modifications on 2024/06/07 Copyright 2024 Capgemini
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
from flask import jsonify, make_response, request, session
from werkzeug.exceptions import BadRequest

from sos_trades_api.controllers.sostrades_data.link_controller import (
    create_link,
    delete_link,
    get_link,
    get_links,
    update_link,
)
from sos_trades_api.server.base_server import app
from sos_trades_api.tools.authentication.authentication import (
    auth_required,
)


@app.route('/api/data/link', methods=['GET'])
@auth_required
def index():
    resp = make_response(jsonify(get_links()), 200)
    return resp


@app.route('/api/data/link/<int:link_identifier>', methods=['GET'])
@auth_required
def get_link_by_id(link_identifier):
    """
    Get a specific link from database
    :param link_identifier: link identifier to retrieve
    """

    if link_identifier is None or link_identifier <= 0:
        raise BadRequest(f'Invalid argument value for link_identifier.\nReceived {link_identifier}, expected stricly positive integer')

    resp = make_response(jsonify(get_link(link_identifier)), 200)
    return resp


@app.route('/api/data/link', methods=['POST'])
@auth_required
def create():
    """
    Create a new Link in database
    """

    user = session['user']
    url = request.json.get('url', None)
    label = request.json.get('label', None)
    description = request.json.get('description', None)

    missing_parameter = []
    if url is None or len(url) == 0:
        missing_parameter.append('Missing mandatory parameter: url')
    if label is None or len(label) == 0:
        missing_parameter.append('Missing mandatory parameter: label')
    if description is None or len(description) == 0:
        missing_parameter.append('Missing mandatory parameter: description')

    if len(missing_parameter) > 0:
        raise BadRequest(missing_parameter)

    created_link = create_link(url, label, description, user.id)

    resp = make_response(jsonify(created_link), 200)
    return resp


@app.route('/api/data/link/<int:link_identifier>', methods=['POST'])
@auth_required
def update_link_by_id(link_identifier):
    """
    update a specific link in database
    :param link_identifier: link identifier to retrieve
    """

    user = session['user']

    if link_identifier is None or link_identifier <= 0:
        raise BadRequest(f'Invalid argument value for link_identifier.\nReceived {link_identifier}, expected strictly positive integer')

    id = request.json.get('id', None)
    url = request.json.get('url', None)
    label = request.json.get('label', None)
    description = request.json.get('description', None)

    if not id == link_identifier:
        raise BadRequest('Invalid payload identifier regard url parameter')

    missing_parameter = []
    if url is None or len(url) == 0:
        missing_parameter.append('Missing mandatory parameter: url')
    if label is None or len(label) == 0:
        missing_parameter.append('Missing mandatory parameter: label')
    if description is None or len(description) == 0:
        missing_parameter.append('Missing mandatory parameter: description')

    if len(missing_parameter) > 0:
        raise BadRequest(missing_parameter)

    if len(missing_parameter) > 0:
        raise BadRequest(missing_parameter)

    resp = make_response(jsonify(update_link(link_identifier, url, label, description, user.id)), 200)
    return resp


@app.route('/api/data/link/<int:link_identifier>', methods=['DELETE'])
@auth_required
def delete_link_by_id(link_identifier):

    if link_identifier is None or link_identifier <= 0:
        raise BadRequest(
            f'Invalid argument value for link_identifier.\nReceived {link_identifier}, expected stricly positive integer')

    delete_link(link_identifier)

    resp = make_response("", 204)
    return resp




