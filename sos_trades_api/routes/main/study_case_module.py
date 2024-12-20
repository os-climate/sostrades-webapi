'''
Copyright 2022 Airbus SAS
Modifications on 2023/08/30-2023/11/24 Copyright 2023 Capgemini

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
import json
import time

from flask import abort, jsonify, make_response, request, send_file, session
from werkzeug.exceptions import BadRequest, MethodNotAllowed

from sos_trades_api.controllers.sostrades_main.study_case_controller import (
    copy_study_discipline_data,
    delete_study_cases,
    export_study_parameters_from_datasets_mapping,
    get_dataset_export_error_message,
    get_dataset_export_status,
    get_dataset_import_error_message,
    get_file_stream,
    get_markdown_documentation,
    get_study_data_file_path,
    get_study_data_stream,
    get_study_load_status,
    load_or_create_study_case,
    load_study_case,
    save_study_is_active,
    set_study_data_file,
    update_study_parameters,
    update_study_parameters_from_datasets_mapping,
)
from sos_trades_api.models.database_models import AccessRights
from sos_trades_api.models.loaded_study_case import LoadStatus
from sos_trades_api.server.base_server import app
from sos_trades_api.tools.authentication.authentication import auth_required
from sos_trades_api.tools.right_management.functional.study_case_access_right import (
    StudyCaseAccess,
)


@app.route("/api/main/study-case/<int:study_id>", methods=["DELETE"])
@auth_required
def delete_study_cases(study_id):
    
    if request.method == "DELETE":
        user = session["user"]
        studies = request.json.get("studies")

        if studies is not None:
            # Checking if user can access study data
            for study_id in studies:
                # Verify user has study case authorisation to delete study
                # (Manager)
                study_case_access = StudyCaseAccess(user.id, study_id)
                if not study_case_access.check_user_right_for_study(AccessRights.MANAGER, study_id):
                    raise BadRequest(
                        "You do not have the necessary rights to delete this study case")

            # Proceeding after rights verification
            resp = make_response(
                jsonify(delete_study_cases(studies)), 200)
            return resp

        raise BadRequest(
            "Missing mandatory parameter: study identifier in url")
    else:
        raise MethodNotAllowed()


@app.route("/api/main/study-case/<int:study_id>", methods=["GET"])
@auth_required
def main_load_study_case_by_id(study_id):

    if study_id is not None:
        start_request_time = time.time()

        # Checking if user can access study data
        user = session["user"]
        # Verify user has study case authorisation to load study (Restricted
        # viewer)
        study_case_access = StudyCaseAccess(user.id, study_id)
        study_case_access_duration = time.time()
        app.logger.info(f"User {user.id:<5} => study_case_access_duration {study_case_access_duration - start_request_time:<5} sec")

        if not study_case_access.check_user_right_for_study(AccessRights.RESTRICTED_VIEWER, study_id):
            raise BadRequest(
                "You do not have the necessary rights to load this study case")
        check_user_right_for_study_duration = time.time()
        app.logger.info(f"User {user.id:<5} => check_user_right_for_study_duration {check_user_right_for_study_duration - study_case_access_duration:<5} sec")

        study_access_right = study_case_access.get_user_right_for_study(
            study_id)
        study_access_right_duration = time.time()
        app.logger.info(
            f"User {user.id:<5} => get_user_right_for_study {study_access_right_duration - check_user_right_for_study_duration:<5} sec")

        loadedStudy = load_or_create_study_case(user.id, study_id, study_access_right)
        loadedStudy_duration = time.time()
        app.logger.info(
            f"User {user.id:<5} => loadedStudy_duration {loadedStudy_duration - study_access_right_duration :<5} sec")

        # Proceeding after rights verification
        resp = make_response(
            jsonify(loadedStudy), 200)
        make_response_duration = time.time()
        app.logger.info(
            f"User {user.id:<5} => make_response_duration {make_response_duration - loadedStudy_duration:<5} sec")
        return resp

    abort(403)


@app.route("/api/main/study-case/<int:study_id>/<int:notification_id>/import-datasets-mapping", methods=["POST"])
@auth_required
def update_study_from_datasets_mapping(study_id, notification_id):
    if study_id is not None and notification_id is not None:
        user = session["user"]
        # Verify user has study case authorisation to load study (Contributor)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(AccessRights.CONTRIBUTOR, study_id):
            raise BadRequest(
                "You do not have the necessary rights to modify this study case")

        # Proceeding after rights verification
        files_data = None
        if "datasets_mapping_file" in request.files:
            try:
                file_content = request.files["datasets_mapping_file"].read().decode("utf-8")
                files_data = json.loads(file_content)

            except Exception as ex:
                raise BadRequest(f"Invalid JSON format : {ex}")
        else:
            raise BadRequest("Missing mandatory datasets_mapping_file")

        resp = make_response(
            jsonify(update_study_parameters_from_datasets_mapping(study_id, user, files_data, notification_id)), 200)
        return resp

    raise BadRequest("Missing mandatory parameter: study or notification identifier in url")

@app.route("/api/main/study-case/<int:study_id>/<int:notification_id>/export-datasets-mapping", methods=["POST"])
@auth_required
def export_study_from_datasets_mapping(study_id, notification_id):
    if study_id is not None and notification_id is not None:
        user = session["user"]
        # Verify user has study case authorisation to load study (Contributor)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(AccessRights.CONTRIBUTOR, study_id):
            raise BadRequest(
                "You do not have the necessary rights to modify this study case")

        # Proceeding after rights verification
        files_data = None
        if "datasets_mapping_file" in request.files:
            try:
                file_content = request.files["datasets_mapping_file"].read().decode("utf-8")
                files_data = json.loads(file_content)

            except Exception as ex:
                raise BadRequest(f"Invalid JSON format : {ex}")
        else:
            raise BadRequest("Missing mandatory datasets_mapping_file")

        resp = make_response(
            jsonify(export_study_parameters_from_datasets_mapping(study_id, user, files_data, notification_id)), 200)
        return resp

    raise BadRequest("Missing mandatory parameter: study or notification identifier in url")

@app.route("/api/main/study-case/<int:study_id>/<int:notification_id>/export-datasets-status", methods=["GET"])
@auth_required
def get_export_study_in_datasets_status(study_id, notification_id):
    if study_id is not None and notification_id is not None:
        user = session["user"]
        # Verify user has study case authorisation to load study (Contributor)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(AccessRights.CONTRIBUTOR, study_id):
            raise BadRequest(
                "You do not have the necessary rights to get this study case")
        resp = make_response(
            jsonify(get_dataset_export_status(study_id, notification_id)), 200)
        return resp

    raise BadRequest("Missing mandatory parameter: study or notification identifier in url")

@app.route("/api/main/study-case/<int:study_id>/<int:notification_id>/export-datasets-error", methods=["GET"])
@auth_required
def get_export_study_in_datasets_error(study_id, notification_id):
    if study_id is not None and notification_id is not None:
        user = session["user"]
        # Verify user has study case authorisation to load study (Contributor)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(AccessRights.CONTRIBUTOR, study_id):
            raise BadRequest(
                "You do not have the necessary rights to get this study case")
        resp = make_response(
            jsonify(get_dataset_export_error_message(study_id, notification_id)), 200)
        return resp

    raise BadRequest("Missing mandatory parameter: study or notification identifier in url")

@app.route("/api/main/study-case/<int:study_id>/import-datasets-error-message", methods=["GET"])
@auth_required
def get_datasets_import_error_message(study_id):
    if study_id is not None:
        user = session["user"]
        # Verify user has study case authorisation to load study (Contributor)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(AccessRights.CONTRIBUTOR, study_id):
            raise BadRequest(
                "You do not have the necessary rights to modify this study case")

        resp = make_response(
            jsonify(get_dataset_import_error_message(study_id)), 200)
        return resp

    raise BadRequest("Missing mandatory parameter: study identifier in url")



@app.route("/api/main/study-case/<int:study_id>/parameters", methods=["POST"])
@auth_required
def update_study_parameters_by_study_case_id(study_id):

    if study_id is not None:
        user = session["user"]
        # Verify user has study case authorisation to load study (Contributor)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(AccessRights.CONTRIBUTOR, study_id):
            raise BadRequest(
                "You do not have the necessary rights to modify this study case")

        # Proceeding after rights verification
        files_data = None
        if "file" in request.files:
            files_data = request.files.getlist("file")

        file_info = None
        if "file_info" in request.form:
            file_info = json.loads(request.form["file_info"])

        parameters = None
        if "parameters" in request.form:
            parameters = json.loads(request.form["parameters"])

        columns_to_delete = []
        if "column_deleted" in request.form:
            columns_to_delete = json.loads(request.form["column_deleted"])

        missing_parameter = []
        if files_data is None or file_info is None:
            missing_parameter.append(
                "Missing mandatory files data source or information")
        if parameters is None:
            missing_parameter.append(
                "Missing mandatory parameter: parameters")

        if len(missing_parameter) > 1:
            raise BadRequest("\n".join(missing_parameter))

        resp = make_response(
            jsonify(update_study_parameters(study_id, user, files_data, file_info, parameters, columns_to_delete)), 200)
        return resp

    raise BadRequest("Missing mandatory parameter: study identifier in url")


@app.route("/api/main/study-case/<int:study_id>/parameter/download", methods=["POST"])
@auth_required
def get_study_parameter_file_by_study_case_id(study_id):
    if study_id is not None:

        user = session["user"]
        # Verify user has study case authorisation to load study (Commenter)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(AccessRights.COMMENTER, study_id):
            raise BadRequest(
                "You do not have the necessary rights to retrieve this information about study case")

        # Proceeding after rights verification
        parameter_key = request.json.get("parameter_key", None)

        if parameter_key is None:
            raise BadRequest("Missing mandatory parameter: parameter_key")

        resp = send_file(get_file_stream(study_id, parameter_key),
                         mimetype="arrayBuffer")
        return resp

    raise BadRequest("Missing mandatory parameter: study identifier in url")


@app.route("/api/main/study-case/<int:study_id>/download", methods=["POST"])
@auth_required
def get_study_data_file_by_study_case_id(study_id):
    if study_id is not None:
        user = session["user"]
        # Verify user has study case authorisation to load study (Commenter)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(AccessRights.COMMENTER, study_id):
            raise BadRequest(
                "You do not have the necessary rights to retrieve this information about study case")

        # Proceeding after rights verification
        file_path = get_study_data_stream(study_id)
        return send_file(file_path)
    raise BadRequest("Missing mandatory parameter: study identifier in url")


@app.route("/api/main/study-case/<int:study_id>/markdown-documentation", methods=["POST"])
@auth_required
def get_markdown_documentation_by_study_case_id(study_id):
    if study_id is not None:
        user = session["user"]
        # Verify user has study case authorisation to load study (Commenter)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(AccessRights.COMMENTER, study_id):
            raise BadRequest(
                "You do not have the necessary rights to retrieve this information about study case")
        
        discipline_key = request.form.get("discipline_key", None)
        if discipline_key is None:
            raise BadRequest("Missing mandatory parameter: discipline key")
        

        resp = make_response(
            jsonify(get_markdown_documentation(study_id, discipline_key)), 200)
        
        return resp
    raise BadRequest("Missing mandatory parameter: study identifier in url")


@app.route("/api/main/study-case/<int:study_id>/download/raw", methods=["POST"])
@auth_required
def get_study_data_raw_file_by_study_case_id(study_id):
    if study_id is not None:
        user = session["user"]
        # Verify user has study case authorisation to load study (Commenter)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(AccessRights.COMMENTER, study_id):
            raise BadRequest(
                "You do not have the necessary rights to retrieve this information about study case")

        # Proceeding after rights verification
        file_path = get_study_data_file_path(study_id)
        return send_file(file_path)
    raise BadRequest("Missing mandatory parameter: study identifier in url")


@app.route("/api/main/study-case/<int:study_id>/upload/raw", methods=["POST"])
@auth_required
def set_study_data_raw_file_by_study_case_id(study_id):

    if study_id is not None:
        user = session["user"]
        # Verify user has study case authorisation to load study (Contributor)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(AccessRights.CONTRIBUTOR, study_id):
            raise BadRequest(
                "You do not have the necessary rights to modify this study case")

        # Proceeding after rights verification
        set_study_data_file(study_id, request.files)
        resp = make_response(jsonify(""), 200)
        return resp

    raise BadRequest("Missing mandatory parameter: study identifier in url")


@app.route("/api/main/study-case/<int:study_id>/copy/discipline-input-data", methods=["POST"])
@auth_required
def copy_study_discipline_data_by_study_case_id(study_id):

    if study_id is not None:
        user = session["user"]
        # Verify user has study case authorisation to load study (Contributor)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(AccessRights.CONTRIBUTOR, study_id):
            raise BadRequest(
                "You do not have the necessary rights to retrieve this information about study case")

        # Proceeding after rights verification
        discipline_from = request.json.get("discipline_from", None)
        discipline_to = request.json.get("discipline_to", None)

        missing_parameter = []
        if discipline_from is None:
            missing_parameter.append(
                "Missing mandatory parameter: discipline_from")
        if discipline_to is None:
            missing_parameter.append(
                "Missing mandatory parameter: discipline_to")

        if len(missing_parameter) > 0:
            raise BadRequest("\n".join(missing_parameter))

        resp = make_response(
            jsonify(copy_study_discipline_data(study_id, discipline_from, discipline_to)), 200)
        return resp

    raise BadRequest("Missing mandatory parameter: study identifier in url")


@app.route("/api/main/study-case/<int:study_id>/reload", methods=["Get"])
@auth_required
def reload_study_discipline_data_by_study_case_id(study_id):
    if study_id is not None:
        #TODO: to test!
        user = session["user"]

        # Verify user has study case authorisation to load study (Restricted
        # viewer)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(AccessRights.RESTRICTED_VIEWER, study_id):
            raise BadRequest(
                "You do not have the necessary rights to load this study case")
        study_access_right = study_case_access.get_user_right_for_study(
            study_id)


        load_study_case(study_id, True)

        # Proceeding after rights verification
        resp = make_response(
            jsonify(True), 200)

        return resp

    abort(403)


@app.route("/api/main/study-case/<int:study_id>/read-only-mode", methods=["GET"])
@auth_required
def load_study_data_in_read_only_mode(study_id):
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

        loadedStudyJson = get_study_case(user.id, study_id, study_access_right, read_only_mode=True)
        resp = make_response(jsonify(loadedStudyJson), 200)
        return resp
    raise BadRequest("Missing mandatory parameter: study identifier in url")


@app.route("/api/main/study-case/<int:study_id>/is-active", methods=["POST"])
@auth_required
def store_study_last_active_date(study_id):
    """
    Save the date of the last user activity on the study
    """
    if study_id is not None:
        user = session["user"]
        # Verify user has study case authorisation to load study (Commenter)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(AccessRights.RESTRICTED_VIEWER, study_id):
            raise BadRequest(
                "You do not have the necessary rights to retrieve this information about this study case")


        save_study_is_active(study_id)

        resp = make_response(jsonify("OK"),200)
        return resp
    raise BadRequest("Missing mandatory parameter: study identifier in url")


@app.route("/api/main/study-case/<int:study_id>/is-up-and-loaded", methods=["Get"])
@auth_required
def check_study_is_loaded(study_id):
    """
    Check if the study is loaded
    """
    if study_id is not None:
        user = session["user"]
        # Verify user has study case authorisation to load study (Commenter)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(AccessRights.RESTRICTED_VIEWER, study_id):
            raise BadRequest(
                "You do not have the necessary rights to retrieve this information about this study case")

        # check studycase is loaded
        loadedStatus = get_study_load_status(study_id)
        resp = make_response(jsonify(loadedStatus != LoadStatus.NONE),200)
        return resp
    raise BadRequest("Missing mandatory parameter: study identifier in url")



