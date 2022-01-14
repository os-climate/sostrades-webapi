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
from sos_trades_api.controllers.sostrades_main.reference_controller import generate_reference


@app.route(f'/api/main/reference', methods=['POST'])
@auth_required
def study_case_references():
    if request.method == 'POST':
        user = get_authenticated_user()

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
