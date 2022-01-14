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
from flask import request, jsonify, make_response, send_file

from werkzeug.exceptions import BadRequest
from sos_trades_api.base_server import app
from sos_trades_api.tools.authentication.authentication import auth_required, get_authenticated_user
from sos_trades_api.controllers.sostrades_data.reference_controller import (
    get_all_references, get_logs, get_reference_generation_status,  get_references_generation_status)


@app.route(f'/api/data/reference', methods=['GET'])
@auth_required
def study_case_references():
    if request.method == 'GET':
        user = get_authenticated_user()
        resp = make_response(
            jsonify(get_all_references(user.id, app.logger)), 200)
        return resp


@app.route(f'/api/data/reference/<int:ref_gen_id>/status', methods=['GET'])
@auth_required
def reference_generation_status(ref_gen_id):
    if ref_gen_id is not None:
        resp = make_response(
            jsonify(get_reference_generation_status(ref_gen_id)), 200)
        return resp


@app.route(f'/api/data/reference/status', methods=['POST'])
@auth_required
def references_generation_status():
    references_list = request.json.get('references_list', None)
    if references_list is None:
        raise BadRequest('Missing mandatory parameter: references_list')
    resp = make_response(
        jsonify(get_references_generation_status(references_list)), 200)
    return resp


@app.route(f'/api/data/reference/logs/download/', methods=['POST'])
@auth_required
def get_reference_generation_logs():

    reference_path = request.json.get('reference_path', None)

    if reference_path is None:
        raise BadRequest('Missing mandatory parameter: reference_path')
    file_path = get_logs(reference_path=reference_path)
    if file_path:
        resp = send_file(file_path)
        return resp
    else:
        resp = make_response(jsonify('No logs found.'), 404)
        return resp
