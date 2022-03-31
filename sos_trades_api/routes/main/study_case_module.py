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
from flask import request, abort, jsonify, make_response, send_file, session

from werkzeug.exceptions import BadRequest
import json
from sos_trades_api.models.database_models import AccessRights
from sos_trades_api.base_server import app
from sos_trades_api.tools.authentication.authentication import auth_required
from sos_trades_api.controllers.sostrades_main.study_case_controller import (
    create_study_case, load_study_case, delete_study_cases, copy_study_discipline_data, get_file_stream,
    update_study_parameters, get_study_data_stream, copy_study_case, get_study_data_file_path)
from sos_trades_api.tools.right_management.functional.process_access_right import ProcessAccess
from sos_trades_api.tools.right_management.functional.study_case_access_right import StudyCaseAccess


@app.route(f'/api/main/study-case', methods=['GET', 'POST', 'DELETE'])
@auth_required
def study_cases():
    if request.method == 'POST':
        user = session['user']

        name = request.json.get('name', None)
        repository = request.json.get('repository', None)
        process = request.json.get('process', None)
        group_id = request.json.get('group', None)
        reference = request.json.get('reference', None)
        from_type = request.json.get('type', None)

        # Verify user has process authorisation to create study
        process_access = ProcessAccess(user.id)
        if not process_access.check_user_right_for_process(AccessRights.CONTRIBUTOR, process, repository):
            raise BadRequest(
                'You do not have the necessary rights to create a study case from this process')

        # Proceed after right verification
        missing_parameter = []
        if name is None:
            missing_parameter.append('Missing mandatory parameter: name')
        if repository is None:
            missing_parameter.append('Missing mandatory parameter: repository')
        if process is None:
            missing_parameter.append('Missing mandatory parameter: process')
        if group_id is None:
            missing_parameter.append('Missing mandatory parameter: group')

        if len(missing_parameter) > 0:
            raise BadRequest('\n'.join(missing_parameter))

        resp = make_response(jsonify(create_study_case(
            user.id, name, repository, process, group_id, reference, from_type)), 200)
        return resp
    else:
        user = session['user']
        studies = request.json.get('studies')

        if studies is not None:
            # Checking if user can access study data
            for study_id in studies:
                # Verify user has study case authorisation to delete study
                # (Manager)
                study_case_access = StudyCaseAccess(user.id)
                if not study_case_access.check_user_right_for_study(AccessRights.MANAGER, study_id):
                    raise BadRequest(
                        'You do not have the necessary rights to delete this study case')

            # Proceeding after rights verification
            resp = make_response(
                jsonify(delete_study_cases(studies)), 200)
            return resp

        raise BadRequest(
            'Missing mandatory parameter: study identifier in url')


@app.route(f'/api/main/study-case/<int:study_id>', methods=['GET'])
@auth_required
def load_study_case_by_id(study_id):

    if study_id is not None:

        # Checking if user can access study data
        user = session['user']

        # Verify user has study case authorisation to load study (Restricted
        # viewer)
        study_case_access = StudyCaseAccess(user.id)
        if not study_case_access.check_user_right_for_study(AccessRights.RESTRICTED_VIEWER, study_id):
            raise BadRequest(
                'You do not have the necessary rights to load this study case')
        study_access_right = study_case_access.get_user_right_for_study(
            study_id)
        
        loadedStudy = load_study_case(study_id, study_access_right, user.id)
                
        # Proceeding after rights verification
        resp = make_response(
            jsonify(loadedStudy), 200)

        return resp

    abort(403)


@app.route(f'/api/main/study-case/<int:study_id>/copy', methods=['POST'])
@auth_required
def copy_study_case_by_id(study_id):

    if study_id is not None:
        user = session['user']

        new_name = request.json.get('new_name', None)
        group_id = request.json.get('group_id', None)

        missing_parameter = []
        if new_name is None:
            missing_parameter.append('Missing mandatory parameter: new_name')
        if group_id is None:
            missing_parameter.append('Missing mandatory parameter: group_id')

        if len(missing_parameter) > 0:
            raise BadRequest('\n'.join(missing_parameter))

        # Verify user has study case authorisation to load study (Contributor)
        study_case_access = StudyCaseAccess(user.id)
        if not study_case_access.check_user_right_for_study(AccessRights.CONTRIBUTOR, study_id):
            raise BadRequest(
                'You do not have the necessary rights to copy this study case')

        # Proceeding after rights verification
        resp = make_response(jsonify(copy_study_case(
            study_id, new_name, group_id, user.id)), 200)

        return resp

    abort(403)


@app.route(f'/api/main/study-case/<int:study_id>/parameters', methods=['POST'])
@auth_required
def update_study_parameters_by_study_case_id(study_id):

    if study_id is not None:
        user = session['user']
        # Verify user has study case authorisation to load study (Contributor)
        study_case_access = StudyCaseAccess(user.id)
        if not study_case_access.check_user_right_for_study(AccessRights.CONTRIBUTOR, study_id):
            raise BadRequest(
                'You do not have the necessary rights to modify this study case')

        # Proceeding after rights verification
        files_data = None
        if 'file' in request.files:
            files_data = request.files.getlist('file')

        file_info = None
        if 'file_info' in request.form:
            file_info = json.loads(request.form['file_info'])

        parameters = None
        if 'parameters' in request.form:
            parameters = json.loads(request.form['parameters'])

        missing_parameter = []
        if files_data is None or file_info is None:
            missing_parameter.append(
                'Missing mandatory files data source or information')
        if parameters is None:
            missing_parameter.append(
                'Missing mandatory parameter: parameters')

        if len(missing_parameter) > 1:
            raise BadRequest('\n'.join(missing_parameter))

        resp = make_response(
            jsonify(update_study_parameters(study_id, user, files_data, file_info, parameters)), 200)
        return resp

    raise BadRequest('Missing mandatory parameter: study identifier in url')


@app.route(f'/api/main/study-case/<int:study_id>/parameter/download', methods=['POST'])
@auth_required
def get_study_parameter_file_by_study_case_id(study_id):
    if study_id is not None:

        user = session['user']
        # Verify user has study case authorisation to load study (Commenter)
        study_case_access = StudyCaseAccess(user.id)
        if not study_case_access.check_user_right_for_study(AccessRights.COMMENTER, study_id):
            raise BadRequest(
                'You do not have the necessary rights to retrieve this information about study case')

        # Proceeding after rights verification
        parameter_key = request.json.get('parameter_key', None)

        if parameter_key is None:
            raise BadRequest('Missing mandatory parameter: parameter_key')

        resp = send_file(get_file_stream(study_id, parameter_key),
                         mimetype='arrayBuffer')
        return resp

    raise BadRequest('Missing mandatory parameter: study identifier in url')


@app.route(f'/api/main/study-case/<int:study_id>/download', methods=['POST'])
@auth_required
def get_study_data_file_by_study_case_id(study_id):
    if study_id is not None:
        user = session['user']
        # Verify user has study case authorisation to load study (Commenter)
        study_case_access = StudyCaseAccess(user.id)
        if not study_case_access.check_user_right_for_study(AccessRights.COMMENTER, study_id):
            raise BadRequest(
                'You do not have the necessary rights to retrieve this information about study case')

        # Proceeding after rights verification
        file_path = get_study_data_file_path(study_id)
        return send_file(file_path)
    raise BadRequest('Missing mandatory parameter: study identifier in url')


@app.route(f'/api/main/study-case/<int:study_id>/download/raw', methods=['POST'])
@auth_required
def get_study_data_file_by_study_case_id(study_id):
    if study_id is not None:
        user = session['user']
        # Verify user has study case authorisation to load study (Commenter)
        study_case_access = StudyCaseAccess(user.id)
        if not study_case_access.check_user_right_for_study(AccessRights.COMMENTER, study_id):
            raise BadRequest(
                'You do not have the necessary rights to retrieve this information about study case')

        # Proceeding after rights verification
        file_path = get_study_data_stream(study_id)
        return send_file(file_path)
    raise BadRequest('Missing mandatory parameter: study identifier in url')


@app.route(f'/api/main/study-case/<int:study_id>/copy/discipline-input-data', methods=['POST'])
@auth_required
def copy_study_discipline_data_by_study_case_id(study_id):

    if study_id is not None:
        user = session['user']
        # Verify user has study case authorisation to load study (Contributor)
        study_case_access = StudyCaseAccess(user.id)
        if not study_case_access.check_user_right_for_study(AccessRights.CONTRIBUTOR, study_id):
            raise BadRequest(
                'You do not have the necessary rights to retrieve this information about study case')

        # Proceeding after rights verification
        discipline_from = request.json.get('discipline_from', None)
        discipline_to = request.json.get('discipline_to', None)

        missing_parameter = []
        if discipline_from is None:
            missing_parameter.append(
                'Missing mandatory parameter: discipline_from')
        if discipline_to is None:
            missing_parameter.append(
                'Missing mandatory parameter: discipline_to')

        if len(missing_parameter) > 0:
            raise BadRequest('\n'.join(missing_parameter))

        resp = make_response(
            jsonify(copy_study_discipline_data(study_id, discipline_from, discipline_to)), 200)
        return resp

    raise BadRequest('Missing mandatory parameter: study identifier in url')


@app.route(f'/api/main/study-case/<int:study_id>/reload', methods=['Get'])
@auth_required
def reload_study_discipline_data_by_study_case_id(study_id):
    if study_id is not None:

        user = session['user']

        # Verify user has study case authorisation to load study (Restricted
        # viewer)
        study_case_access = StudyCaseAccess(user.id)
        if not study_case_access.check_user_right_for_study(AccessRights.RESTRICTED_VIEWER, study_id):
            raise BadRequest(
                'You do not have the necessary rights to load this study case')
        study_access_right = study_case_access.get_user_right_for_study(
            study_id)

        loadedStudy = load_study_case(study_id, study_access_right, user.id, True)

        # Proceeding after rights verification
        resp = make_response(
            jsonify(loadedStudy), 200)

        return resp

    abort(403)