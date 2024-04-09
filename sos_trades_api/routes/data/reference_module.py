'''
Copyright 2022 Airbus SAS
Modifications on 2023/12/04 Copyright 2023 Capgemini

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
from sos_trades_api.tools.right_management.access_right import has_access_to, APP_MODULE_EXECUTION

from werkzeug.exceptions import BadRequest
from sos_trades_api.server.base_server import app
from sos_trades_api.tools.authentication.authentication import auth_required, get_authenticated_user
from sos_trades_api.controllers.sostrades_data.reference_controller import (
    get_all_references, get_logs, get_reference_flavor, get_reference_generation_status_by_id, generate_reference, stop_generation, update_reference_flavor)


@app.route(f'/api/data/reference', methods=['GET', 'POST'])
@auth_required
def study_case_references():
    if request.method == 'GET':
        user = get_authenticated_user()
        resp = make_response(
            jsonify(get_all_references(user.id, app.logger)), 200)
        return resp
    if request.method == 'POST':
        user = get_authenticated_user()
        if (not has_access_to(user.user_profile_id, APP_MODULE_EXECUTION)):
            app.logger.warning(
                f'Start generation request, user not allowed to generate a reference')
            raise BadRequest(
                'You do not have the necessary rights to generate this reference')

        repository_name = request.json.get('repository_name', None)
        process_name = request.json.get('process_name', None)
        usecase_name = request.json.get('usecase_name', None)

        if repository_name is None:
            raise BadRequest('Missing mandatory parameter: repository_name')
        if process_name is None:
            raise BadRequest('Missing mandatory parameter: process_name')
        if usecase_name is None:
            raise BadRequest('Missing mandatory parameter: usecase_name')
        resp = make_response(
            jsonify(generate_reference(repository_name, process_name, usecase_name, user.id)), 200)
        return resp

@app.route(f'/api/data/reference/<int:ref_gen_id>/update-flavor', methods=['POST'])
@auth_required
def reference_update_flavor(ref_gen_id):
    if ref_gen_id is None:
        raise BadRequest('Missing mandatory parameter: reference id')
    if ref_gen_id is not None:
        flavor = request.json.get('flavor', None)
        resp = make_response(
            jsonify(update_reference_flavor(ref_gen_id, flavor)), 200)
        return resp
    
@app.route(f'/api/data/reference/<int:ref_gen_id>/get-flavor', methods=['GET'])
@auth_required
def reference_get_flavor(ref_gen_id):
    if ref_gen_id is None:
        raise BadRequest('Missing mandatory parameter: reference id')
    if ref_gen_id is not None:
        
        resp = make_response(
            jsonify(get_reference_flavor(ref_gen_id)), 200)
        return resp


@app.route(f'/api/data/reference/<int:ref_gen_id>/status', methods=['GET'])
@auth_required
def reference_generation_status(ref_gen_id):
    if ref_gen_id is None:
        raise BadRequest('Missing mandatory parameter: reference id')
    if ref_gen_id is not None:
        resp = make_response(
            jsonify(get_reference_generation_status_by_id(ref_gen_id)), 200)
        return resp


@app.route(f'/api/data/reference/stop/<int:reference_id>', methods=['POST'])
@auth_required
def reference_stop(reference_id):
    if reference_id is not None:
        # Verify user has authorisation to stop execution of reference (execution rights)
        user = get_authenticated_user()
        if (not has_access_to(user.user_profile_id, APP_MODULE_EXECUTION)):
            app.logger.warning(
                f'Stop generation request, user {user.id} is not allowed to stop the generation {reference_id} ')
            raise BadRequest(
                'You do not have the necessary rights to stop the generation of this reference')
        
        # Proceeding after rights verification
        stop_generation(reference_id)
        resp = make_response(jsonify('Generation stopped', 200))
        return resp

    raise BadRequest('Missing mandatory parameter: reference identifier in url')





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
