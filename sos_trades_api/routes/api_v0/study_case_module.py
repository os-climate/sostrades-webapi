# -*- coding: utf-8 -*-
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

import time
from flask import request, make_response, abort, jsonify, send_file, session
from werkzeug.exceptions import BadRequest

from sos_trades_api.base_server import app, study_case_cache
from sos_trades_api.models.database_models import AccessRights, StudyCaseChange
from sos_trades_api.controllers.sostrades_main.study_case_controller import light_load_study_case, load_study_case, \
    update_study_parameters, get_file_stream, copy_study_case
from sos_trades_api.controllers.sostrades_data.study_case_controller import get_raw_logs
from sos_trades_api.tools.loading.loaded_tree_node import flatten_tree_node
from sos_trades_api.tools.authentication.authentication import has_user_access_right, api_key_required
from sos_trades_api.tools.right_management.functional.study_case_access_right import StudyCaseAccess


@app.route(f'/api/v0/study-case/<int:study_id>', methods=['GET'])
@app.route(f'/api/v0/study-case/<int:study_id>/<int:timeout>', methods=['GET'])
@api_key_required
@has_user_access_right(AccessRights.RESTRICTED_VIEWER)
def load_study_case_by_id(study_id: int, timeout: int = 30):
    """
    Return dictionary containing loaded study tree node data

    :return: json response like
        {
            'discipline1': {'discipline1 data'},
            'discipline2': {'discipline2 data'}...
        }
    """

    try:

        user = session['user']
        study_case_access = StudyCaseAccess(user.id)
        study_access_right = study_case_access.get_user_right_for_study(study_id)

        # Trigger load
        load_study_case(study_id, study_access_right, user.id)

        # Wait load complete
        for _ in range(timeout):

            study_manager = light_load_study_case(study_id)

            if study_manager.loaded:
                break
            else:
                time.sleep(1)

        loaded_study = load_study_case(study_id, study_access_right, user.id)

        flattened_tree_node = flatten_tree_node(loaded_study.treenode)
        payload = {}

        if flattened_tree_node:
            # Filter editable inputs or numerical parameters
            flattened_tree_node = {
                disc: disc_values for disc, disc_values in flattened_tree_node.items() if
                disc_values.get("numerical") or
                (disc_values.get("editable") and disc_values.get("io_type") == "in")
            }

            # Filter discipline values
            wanted_keys = ["var_name", "type", "unit", "value", "visibility", "optional"]
            for disc, disc_values in flattened_tree_node.items():
                payload[disc] = {key: value for key, value in disc_values.items() if key in wanted_keys}

        return make_response(jsonify(payload), 200)

    except Exception as e:
        abort(400, str(e))


@app.route(f'/api/v0/study-case/<int:study_id>/copy', methods=['POST'])
@api_key_required
@has_user_access_right(AccessRights.CONTRIBUTOR)
def copy_study_case_by_id(study_id):
    """
      Copy a existing study
      """
    try:
        if study_id is not None:
            user = session['user']
            new_study_name = request.json.get('new_study_name', None)

            if new_study_name is None:
                abort(400, "Missing mandatory parameter: new_name")

            # Retrieve the source study
            copy_study_identifier = copy_study_case(study_id, new_study_name, None, user.id)

            # Proceeding after rights verification
            resp = make_response(jsonify(copy_study_identifier), 200)
            return resp

        else:
            abort(400, 'Missing mandatory parameter: study identifier in url')

    except Exception as e:
        abort(400, str(e))


@app.route(f'/api/v0/study-case/<int:study_id>/parameters', methods=['POST'])
@api_key_required
@has_user_access_right(AccessRights.CONTRIBUTOR)
def update_study_parameters_by_study_case_id(study_id: int):
    """
    Update a study parameters
    """

    user = session['user']

    # Preliminary checks
    if not request.files and not request.json:
        abort(400, "No files or parameters found in request.")

    needed_parameters_keys = ['variableId', 'newValue', 'unit']
    if request.json:
        request_json = request.json if isinstance(request.json, list) else [request.json]

        messages = []
        missing_variable = False
        for parameter_json in request_json:

            for needed_key in needed_parameters_keys:
                if not parameter_json.get(needed_key):
                    messages.append(f'Missing mandatory key: {needed_key}')
                    missing_variable = True
                else:
                    messages.append(f'Mandatory key {needed_key} found with value {parameter_json.get("variableId")}')

        if missing_variable:
            abort(400, "\n".join(messages))

    # Cache study
    light_load_study_case(study_id)

    try:
        files = None
        files_info = None
        parameters_to_save = []

        if request.files:
            files = []
            files_info = {}
            for variable_id, file_io in request.files.items():
                # Rename file
                file_io.filename = variable_id + ".csv"
                files.append(file_io)
                files_info[file_io.filename] = {
                        "variable_id": variable_id,
                        "namespace": tuple(variable_id.rsplit('.', 1))[0],
                        "discipline": "Data"
                }

        if request.json:
            for parameter_json in request_json:

                parameter_json["changeType"] = StudyCaseChange.SCALAR_CHANGE
                parameter_json["oldValue"] = ""  # TODO oldValue est necessaire pour le revert ?
                parameter_json["namespace"], parameter_json["var_name"] = tuple(parameter_json.get("variableId").rsplit('.', 1))
                parameters_to_save.append(parameter_json)

        resp = update_study_parameters(study_id, user, files, files_info, parameters_to_save)
        return make_response(jsonify(resp), 200)

    except Exception as e:
        abort(400, str(e))


@app.route(f'/api/v0/study-case/<int:study_id>/parameter/download', methods=['POST'])
@api_key_required
@has_user_access_right(AccessRights.COMMENTER)
def get_study_parameter_file_by_study_case_id(study_id: int):
    """
    Return fileIO for study parameter
    """
    try:
        if request.json is None:
            abort(400, "'parameter_key' not found in request")

        parameter = request.json.get('parameter_key')

        light_load_study_case(study_id)

        return send_file(get_file_stream(study_id, parameter),
                         mimetype='text/csv')

    except Exception as e:
        abort(400, str(e))


@app.route(f'/api/v0/study-case/<int:study_id>/url', methods=['GET'])
@api_key_required
def get_study_case_url(study_id: int):
    """
    Return study-case web-GUI url

    :return: json response like {'study_url': 'http/link/to/webgui/'}
    """

    try:

        study_case_cache.get_study_case(study_id, False)
        study_url = f'{app.config.get("SOS_TRADES_FRONT_END_DNS", "")}study/{study_id}'

        return make_response(jsonify({"study_url": study_url}), 200)

    except Exception as e:
        abort(400, str(e))


@app.route(f'/api/v0/study-case/<int:study_id>/logs', methods=['GET'])
@api_key_required
@has_user_access_right(AccessRights.COMMENTER)
def get_study_case_raw_logs(study_id):

    file_path = get_raw_logs(study_id=study_id)

    if file_path:
        resp = send_file(file_path)
        return resp
    else:
        resp = make_response(jsonify('No logs found.'), 404)
        return resp


