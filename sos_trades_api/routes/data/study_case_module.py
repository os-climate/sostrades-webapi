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
from flask import request, abort, jsonify, make_response, send_file

from werkzeug.exceptions import BadRequest

from sos_trades_api.models.database_models import AccessRights
from sos_trades_api.base_server import app
from sos_trades_api.tools.authentication.authentication import auth_required, get_authenticated_user
from sos_trades_api.controllers.sostrades_data.study_case_controller import (
    get_change_file_stream, discipline_icon_mapping, get_user_shared_study_case, get_logs, get_raw_logs,
    get_study_case_notifications, get_user_authorised_studies_for_process, load_study_case_preference,
    save_study_case_preference, set_user_authorized_execution)
from sos_trades_api.tools.right_management.functional.study_case_access_right import StudyCaseAccess


@app.route(f'/api/data/study-case', methods=['GET'])
@auth_required
def study_cases():
    if request.method == 'GET':
        app.logger.info(get_authenticated_user())
        user = get_authenticated_user()
        # Transform object array to json convertible
        result = [sc.serialize() for sc in get_user_shared_study_case(user.id)]
        resp = make_response(jsonify(result), 200)
        return resp


@app.route(f'/api/data/study-case/<int:study_id>/parameter/change', methods=['POST'])
@auth_required
def get_study_parameter_change_file_by_study_case_id(study_id):
    if study_id is not None:

        # Checking if user can access study data
        user = get_authenticated_user()
        # Verify user has study case authorisation to load study (Commenter)
        study_case_access = StudyCaseAccess(user.id)
        if not study_case_access.check_user_right_for_study(AccessRights.COMMENTER, study_id):
            raise BadRequest(
                'You do not have the necessary rights to retrieve this information about study case')

        # Proceeding after rights verification
        parameter_key = request.json.get('parameter_key', None)
        notification_id = request.json.get('notification_id', None)

        if parameter_key is None:
            raise BadRequest('Missing mandatory parameter: parameter_key')
        if notification_id is None:
            raise BadRequest('Missing mandatory parameter: notification_id')

        resp = send_file(get_change_file_stream(notification_id, parameter_key),
                         mimetype='arrayBuffer')
        return resp

    raise BadRequest('Missing mandatory parameter: study identifier in url')


@app.route(f'/api/data/study-case/<int:study_id>/access', methods=['GET'])
@auth_required
def check_study_case_access_right(study_id):
    access = False

    if study_id is not None:

        # Checking if user can access study data
        user = get_authenticated_user()

        # Verify user has study case authorisation to load study (Restricted
        # viewer)
        study_case_access = StudyCaseAccess(user.id)
        if study_case_access.check_user_right_for_study(AccessRights.RESTRICTED_VIEWER, study_id):
            access = True

    return make_response(jsonify(access), 200)


@app.route(f'/api/data/study-case/<int:study_id>/notifications', methods=['GET'])
@auth_required
def study_case_notifications(study_id):
    if request.method == 'GET':
        # Checking if user can access study data
        user = get_authenticated_user()
        # Verify user has study case authorisation to get study notifications
        # (Commenter)
        study_case_access = StudyCaseAccess(user.id)
        with_notifications = False
        if study_case_access.check_user_right_for_study(AccessRights.COMMENTER, study_id):
            with_notifications = True

        # Proceeding after rights verification
        resp = make_response(
            jsonify(get_study_case_notifications(study_id, with_notifications)), 200)
        return resp


@app.route(f'/api/data/study-case/process', methods=['POST'])
@auth_required
def get_user_authorized_process_studies():
    user = get_authenticated_user()

    repository_name = request.json.get('repository_name', None)
    process_name = request.json.get('process_name', None)

    if repository_name is None:
        raise BadRequest('Missing mandatory parameter: repository_name')
    if process_name is None:
        raise BadRequest('Missing mandatory parameter: process_name')
    # Proceeding after rights verification
    resp = make_response(
        jsonify(get_user_authorised_studies_for_process(user.id, process_name, repository_name)), 200)
    return resp


@app.route(f'/api/data/study-case/icon-mapping', methods=['get'])
@auth_required
def get_discipline_icon_mapping():
    return make_response(
        jsonify(discipline_icon_mapping()), 200)


@app.route(f'/api/data/study-case/logs/download', methods=['POST'])
@auth_required
def get_study_case_logs():
    user = get_authenticated_user()
    study_id = request.json.get('studyid', None)

    if study_id is None:
        raise BadRequest('Missing mandatory parameter: study_id')
    file_path = get_logs(study_id=study_id)
    if file_path:
        resp = send_file(file_path)
        return resp
    else:
        resp = make_response(jsonify('No logs found.'), 404)
        return resp


@app.route(f'/api/data/study-case/raw-logs/download', methods=['POST'])
@auth_required
def get_study_case_raw_logs():
    user = get_authenticated_user()
    study_id = request.json.get('studyid', None)

    if study_id is None:
        raise BadRequest('Missing mandatory parameter: study_id')
    file_path = get_raw_logs(study_id=study_id)
    if file_path:
        resp = send_file(file_path)
        return resp
    else:
        resp = make_response(jsonify('No logs found.'), 404)
        return resp


@app.route(f'/api/data/study-case/<int:study_id>/preference', methods=['GET', 'POST'])
@auth_required
def load_study_case_preference_by_id(study_id):

    if study_id is not None:

        # Checking if user can access study data
        user = get_authenticated_user()

        # Verify user has study case authorisation to load study (Restricted
        # viewer)
        study_case_access = StudyCaseAccess(user.id)
        if not study_case_access.check_user_right_for_study(AccessRights.RESTRICTED_VIEWER, study_id):
            raise BadRequest(
                'You do not have the necessary rights to load this study case')

        if request.method == 'GET':

            # Proceeding after rights verification
            resp = make_response(
                jsonify(load_study_case_preference(study_id, user.id)), 200)

            return resp
        elif request.method == 'POST':

            preference = request.json.get('preference', None)

            # Proceed after right verification
            missing_parameter = []
            if preference is None:
                missing_parameter.append(
                    'Missing mandatory parameter: preference')

            if len(missing_parameter) > 0:
                raise BadRequest('\n'.join(missing_parameter))

            save_study_case_preference(study_id, user.id, preference)

            resp = make_response(jsonify('Preference saved'), 200)
            return resp

    abort(403)


@app.route(f'/api/data/study-case/<int:study_id>/user/execution', methods=['POST'])
@auth_required
def update_user_authorized_for_execution(study_id):
    if study_id is not None:
        # Checking if user can access study data
        user = get_authenticated_user()
        # Verify user has study case authorisation to load study (Contributor)
        study_case_access = StudyCaseAccess(user.id)
        if not study_case_access.check_user_right_for_study(AccessRights.CONTRIBUTOR, study_id):
            raise BadRequest(
                'You do not have the necessary rights to claim study case execution right')

        # Proceeding after rights verification
        resp = make_response(jsonify(set_user_authorized_execution(study_id, user.id)), 200)
        return resp
    raise BadRequest('Missing mandatory parameter: study identifier in url')
