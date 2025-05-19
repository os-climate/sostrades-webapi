'''
Copyright 2022 Airbus SAS
Modifications on 2023/08/30-2023/11/23 Copyright 2023 Capgemini

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
# -*- coding: utf-8 -*-

import time

from flask import abort, jsonify, make_response, request, send_file, session
from werkzeug.exceptions import BadRequest

from sos_trades_api.controllers.sostrades_data.study_case_controller import (
    create_empty_study_case,
    get_raw_logs,
    add_last_opened_study_case,
)
from sos_trades_api.controllers.sostrades_main.study_case_controller import (
    get_file_stream,
    light_load_study_case,
    load_study_case,
    update_study_parameters,
)
from sos_trades_api.tools.study_management.study_management import (
    get_read_only,
)
from sos_trades_api.controllers.sostrades_data.ontology_controller import load_markdown_documentation_metadata
from sos_trades_api.models.database_models import (
    AccessRights,
    StudyCase,
    StudyCaseChange,
)
from sos_trades_api.models.loaded_study_case import LoadedStudyCase, LoadStatus
from sos_trades_api.server.base_server import app, study_case_cache
from sos_trades_api.tools.authentication.authentication import (
    api_key_required,
    has_user_access_right,
)
from sos_trades_api.tools.loading.loaded_tree_node import flatten_tree_node
from sos_trades_api.tools.right_management.functional.study_case_access_right import (
    StudyCaseAccess,
)
from sos_trades_api.tools.gzip_tools import make_gzipped_response
from sos_trades_api.controllers.sostrades_data.ontology_controller import (
    load_ontology_usages,
)


@app.route("/api/v0/study-case/<int:study_id>", methods=["GET"])
@app.route("/api/v0/study-case/<int:study_id>/<int:timeout>", methods=["GET"])
@api_key_required
@has_user_access_right(AccessRights.RESTRICTED_VIEWER)
def api_v0_load_study_case_by_id(study_id: int, timeout: int = 30):
    """
    Return dictionary containing loaded study tree node data

    :return: json response like
        {
            'discipline1': {'discipline1 data'},
            'discipline2': {'discipline2 data'}...
        }
    """
    try:

        user = session["user"]
        study_case_access = StudyCaseAccess(user.id)
        study_access_right = study_case_access.get_user_right_for_study(study_id)

        # Trigger load
        load_study_case(study_id)

        # Wait load complete
        for _ in range(timeout):

            study_manager = light_load_study_case(study_id)

            if study_manager.load_status == LoadStatus.LOADED:
                break
            else:
                time.sleep(1)
        read_only = study_access_right == AccessRights.COMMENTER
        no_data = study_access_right == AccessRights.RESTRICTED_VIEWER
        loaded_study_case = LoadedStudyCase(study_manager, no_data, read_only, user.id)
        flattened_tree_node = flatten_tree_node(loaded_study_case.study_case.treenode)
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


@app.route("/api/v0/study-case/<int:study_id>/copy", methods=["POST"])
@api_key_required
@has_user_access_right(AccessRights.CONTRIBUTOR)
def copy_study_case_by_id(study_id):
    """
    Copy a existing study
    """
    try:
        if study_id is not None:
            user = session["user"]
            group = session["group"]

            new_study_name = request.json.get("new_study_name", None)

            if new_study_name is None:
                abort(400, "Missing mandatory parameter: new_name")

            source_study_case = None
            with app.app_context():
                source_study_case = StudyCase.query.filter(StudyCase.id == study_id).first()

            study_case = create_empty_study_case(user.id, new_study_name, source_study_case.repository,
                                                 source_study_case.process, group.id, study_id, StudyCase.FROM_STUDYCASE, source_study_case.study_pod_flavor, source_study_case.execution_pod_flavor)

            # Retrieve the source study
            load_study_case(study_case.id)

            # Proceeding after rights verification
            resp = make_response(jsonify(study_case.id), 200)
            return resp

        else:
            abort(400, "Missing mandatory parameter: study identifier in url")

    except Exception as e:
        abort(400, str(e))


@app.route("/api/v0/study-case/<int:study_id>/parameters", methods=["POST"])
@api_key_required
@has_user_access_right(AccessRights.CONTRIBUTOR)
def update_study_parameters_by_study_case_id(study_id: int):
    """
    Update a study parameters
    """
    user = session["user"]

    # Preliminary checks
    if not request.files and not request.json:
        abort(400, "No files or parameters found in request.")

    needed_parameters_keys = ["variableId", "newValue", "unit"]
    if request.json:
        request_json = request.json if isinstance(request.json, list) else [request.json]

        messages = []
        missing_variable = False
        for parameter_json in request_json:

            for needed_key in needed_parameters_keys:
                if needed_key not in parameter_json:
                    messages.append(f"Missing mandatory key: {needed_key}")
                    missing_variable = True
                else:
                    messages.append(f'Mandatory key {needed_key} found with value {parameter_json.get("needed_key")}')

        if missing_variable:
            abort(400, "\n".join(messages))

    # Cache study
    light_load_study_case(study_id)

    try:
        files = None
        files_info = None
        parameters_to_save = []
        columns_to_delete = []

        if request.files:
            files = []
            files_info = {}
            for variable_id, file_io in request.files.items():
                # Rename file
                file_io.filename = variable_id + ".csv"
                files.append(file_io)
                files_info[file_io.filename] = {
                        "variable_id": variable_id,
                        "namespace": tuple(variable_id.rsplit(".", 1))[0],
                        "discipline": "Data",
                }
        if request.json:
            for parameter_json in request_json:
                columns_to_delete = parameter_json.get("column_deleted")
                parameter_json["changeType"] = StudyCaseChange.SCALAR_CHANGE
                parameter_json["oldValue"] = ""  # TODO oldValue est necessaire pour le revert ?
                parameter_json["namespace"], parameter_json["var_name"] = tuple(parameter_json.get("variableId").rsplit(".", 1))
                parameters_to_save.append(parameter_json)

        resp = update_study_parameters(study_id, user, files, files_info, parameters_to_save, columns_to_delete)
        return make_response(jsonify(resp), 200)

    except Exception as e:
        abort(400, str(e))


@app.route("/api/v0/study-case/<int:study_id>/parameter/download", methods=["POST"])
@api_key_required
@has_user_access_right(AccessRights.COMMENTER)
def get_study_parameter_file_by_study_case_id(study_id: int):
    """
    Return fileIO for study parameter
    """
    try:
        if request.json is None:
            abort(400, "'parameter_key' not found in request")

        parameter = request.json.get("parameter_key")

        light_load_study_case(study_id)

        return send_file(get_file_stream(study_id, parameter),
                         mimetype="text/csv")

    except Exception as e:
        abort(400, str(e))


@app.route("/api/v0/study-case/<int:study_id>/url", methods=["GET"])
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


@app.route("/api/v0/study-case/<int:study_id>/logs", methods=["GET"])
@api_key_required
@has_user_access_right(AccessRights.COMMENTER)
def get_study_case_raw_logs(study_id):

    file_path = get_raw_logs(study_id)

    if file_path:
        resp = send_file(file_path)
        return resp
    else:
        resp = make_response(jsonify("No logs found."), 404)
        return resp
    
@app.route("/api/v0/study-case/<int:study_id>/read-only-mode", methods=["GET"])
@api_key_required
@has_user_access_right(AccessRights.COMMENTER)
def load_study_case_by_id_in_read_only(study_id):
    """
    Retreive the study in read only mode, return none if no read only mode found
    """
    if study_id is not None:
        user = session["user"]
        # Verify user has study case authorisation to load study (Commenter)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(AccessRights.RESTRICTED_VIEWER, study_id):
            raise BadRequest(
                "You do not have the necessary rights to retrieve this information about this study case")
        study_access_right = study_case_access.get_user_right_for_study(
            study_id)

        loaded_study_json = get_read_only(study_id, study_access_right)
        # Add this study in last study opened in database
        add_last_opened_study_case(study_id, user.id)
        return make_gzipped_response(loaded_study_json)
    raise BadRequest("Missing mandatory parameter: study identifier in url")

@app.route("/api/v0/ontology/ontology-usages", methods=["POST"])
@api_key_required
def load_ontology_request_usages():
    """
    Relay to ontology server to retrieve disciplines and parameters informations

    Request object is intended with the following data structure
        {
            ontology_request: {
                disciplines: string[], // list of disciplines string identifier
                parameter_usages: string[] // list of parameters string identifier
            }
        }

    Returned response is with the following data structure
        {
            parameter_usages : {
                <parameter_usage_identifier> : {
                    parameter_uri: string
                    parameter_id: string
                    parameter_label: string
                    parameter_definition: string
                    parameter_definitionSource: string
                    parameter_ACLTag: string

                    visibility: string
                    dataframeEditionLocked: string
                    userLevel: string
                    range: string
                    dataframeDescriptor: string
                    structuring: string
                    optional: string
                    namespace: string
                    numerical: string
                    coupling: string
                    io_type: string
                    datatype: string
                    unit: string
                    editable: string
                }
            }
            disciplines {
                <discipline_identifier>: {
                    id: string
                    delivered: string
                    implemented: string
                    label: string
                    modelType: string
                    originSource: string
                    pythonClass: string
                    uri: string
                    validator: string
                    validated: string
                    icon:string
                }
            }
        }

    """
    data_request = request.json.get("ontology_request", None)

    missing_parameter = []
    if data_request is None:
        missing_parameter.append(
            "Missing mandatory parameter: ontology_request")

    if len(missing_parameter) > 0:
        raise BadRequest("\n".join(missing_parameter))

    resp = make_response(jsonify(load_ontology_usages(data_request)), 200)
    return resp


@app.route("/api/v0/ontology/<string:identifier>/markdown_documentation", methods=["GET"])
@api_key_required
def load_markdown_documentation(identifier):
    """
    Relay to ontology server to retrieve the whole sos_trades models links diagram
    Object returned is a form of d3 js data structure

    Returned response is with the following data structure
        {
            Markdown_documentation:
                document: string,
            }
        }
    """
    user = session["user"]
    app.logger.info(user)

    resp = make_response(jsonify(load_markdown_documentation_metadata(identifier)), 200)
    return resp
