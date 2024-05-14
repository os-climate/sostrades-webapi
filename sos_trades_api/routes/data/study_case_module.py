'''
Copyright 2022 Airbus SAS
Modifications on 2023/11/17-2023/11/20 Copyright 2023 Capgemini

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

from werkzeug.exceptions import BadRequest, MethodNotAllowed

from sos_trades_api.models.database_models import AccessRights, StudyCase, UserStudyFavorite
from sos_trades_api.server.base_server import app
from sos_trades_api.tools.authentication.authentication import auth_required
from sos_trades_api.controllers.sostrades_data.study_case_controller import (
    edit_study_execution_flavor, get_change_file_stream, get_study_execution_flavor, get_user_shared_study_case, get_raw_logs, get_user_study_case, study_case_logs,
    get_study_case_notifications, get_user_authorised_studies_for_process, load_study_case_preference,
    save_study_case_preference, set_user_authorized_execution, create_empty_study_case,
    add_favorite_study_case, remove_favorite_study_case, create_study_case_allocation, load_study_case_allocation,
    get_study_case_allocation, delete_study_cases_and_allocation, edit_study, copy_study)
from sos_trades_api.tools.right_management.functional.study_case_access_right import StudyCaseAccess
from sos_trades_api.tools.right_management.functional.process_access_right import ProcessAccess


@app.route(f'/api/data/study-case', methods=['GET'])
@auth_required
def study_cases():
    user = session['user']

    if request.method == 'GET':
        # Transform object array to json convertible
        result = [sc.serialize() for sc in get_user_shared_study_case(user.id)]
        resp = make_response(jsonify(result), 200)
        return resp

    raise MethodNotAllowed()

@app.route(f'/api/data/study-case/<int:study_case_identifier>', methods=['GET'])
@auth_required
def get_study_case(study_case_identifier: int):
    user = session['user']

    if request.method == 'GET':
        # Verify user has study case authorisation to load study (Restricted viewer)
        study_case_access = StudyCaseAccess(user.id, study_case_identifier)
        if not study_case_access.check_user_right_for_study(AccessRights.RESTRICTED_VIEWER, study_case_identifier):
            raise BadRequest(
                'You do not have the necessary rights to load this study case')

        # Transform object array to json convertible
        result = get_user_study_case(user.id, study_case_identifier)
        resp = make_response(jsonify(result), 200)
        return resp

    raise MethodNotAllowed()


@app.route(f'/api/data/study-case', methods=['POST'])
@auth_required
def allocation_for_new_study_case():
    user = session['user']

    if request.method == 'POST':

        name = request.json.get('name', None)
        repository = request.json.get('repository', None)
        process = request.json.get('process', None)
        group_id = request.json.get('group', None)
        reference = request.json.get('reference', None)
        from_type = request.json.get('type', None)
        flavor = request.json.get('flavor', None)

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
        #reference can be None
        if from_type is None:
            missing_parameter.append('Missing mandatory parameter: type')

        if len(missing_parameter) > 0:
            raise BadRequest('\n'.join(missing_parameter))

        study_case = create_empty_study_case(user.id, name, repository, process, group_id, reference, from_type, flavor, flavor)
        new_study_case_allocation = create_study_case_allocation(study_case.id, flavor)

        resp = make_response(jsonify(new_study_case_allocation), 200)
        return resp

    raise MethodNotAllowed()


@app.route(f'/api/data/study-case/<int:study_case_identifier>', methods=['POST'])
@auth_required
def allocation_for_existing_study_case(study_case_identifier: int):
    user = session['user']

    if request.method == 'POST':

        # Verify user has study case authorisation to load study (Restricted viewer)
        study_case_access = StudyCaseAccess(user.id, study_case_identifier)
        if not study_case_access.check_user_right_for_study(AccessRights.RESTRICTED_VIEWER, study_case_identifier):
            raise BadRequest(
                'You do not have the necessary rights to load this study case')

        study_case_allocation = load_study_case_allocation(study_case_identifier)

        # Proceeding after rights verification
        return make_response(jsonify(study_case_allocation), 200)
    else:
        raise MethodNotAllowed()


@app.route(f'/api/data/study-case/<int:study_case_identifier>/by/copy', methods=['POST'])
@auth_required
def allocation_for_copying_study_case(study_case_identifier: int):
    user = session['user']

    if request.method == 'POST':

        new_name = request.json.get('new_name', None)
        group_id = request.json.get('group_id', None)
        flavor = request.json.get('flavor', None)

        # Verify user has study case authorisation to load study (Restricted viewer)
        study_case_access = StudyCaseAccess(user.id, study_case_identifier)
        if not study_case_access.check_user_right_for_study(AccessRights.RESTRICTED_VIEWER, study_case_identifier):
            raise BadRequest(
                'You do not have the necessary rights to create a study case from this process')

        # Proceed after right verification
        missing_parameter = []
        if new_name is None:
            missing_parameter.append('Missing mandatory parameter: new_name')
        if group_id is None:
            missing_parameter.append('Missing mandatory parameter: group_id')

        if len(missing_parameter) > 0:
            raise BadRequest('\n'.join(missing_parameter))

        source_study_case = None
        with app.app_context():
            source_study_case = StudyCase.query.filter(StudyCase.id == study_case_identifier).first()

        study_case = create_empty_study_case(user.id, new_name, source_study_case.repository, source_study_case.process, 
                                             group_id, str(study_case_identifier), StudyCase.FROM_STUDYCASE, 
                                             flavor, source_study_case.execution_pod_flavor)
        new_study_case_allocation = create_study_case_allocation(study_case.id, source_study_case.study_pod_flavor)

        resp = make_response(jsonify(new_study_case_allocation), 200)
        return resp
    else:
        raise MethodNotAllowed()


@app.route(f'/api/data/study-case/<int:study_id>/status', methods=['GET'])
@auth_required
def study_case_allocation_status(study_id):

    if study_id is not None:

        # Checking if user can access study data
        user = session['user']

        # Verify user has study case authorisation to load study (Restricted
        # viewer)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(AccessRights.RESTRICTED_VIEWER, study_id):
            raise BadRequest(
                'You do not have the necessary rights to load this study case')
        study_access_right = study_case_access.get_user_right_for_study(
            study_id)

        # Proceeding after rights verification
        resp = make_response(
            jsonify(get_study_case_allocation(study_id)), 200)

        return resp

    abort(403)


@app.route(f'/api/data/study-case/<int:study_id>/copy', methods=['POST'])
@auth_required
def copy_study_case(study_id):

    if study_id is not None:
        # Checking if user can access study data
        user = session['user']

        group_id = request.json.get('group_id', None)
        study_name = request.json.get('new_study_name', None)
        flavor = request.json.get('flavor', None)

        # Verify user has study case authorisation to update study (Manager)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(AccessRights.MANAGER, study_id):
            raise BadRequest(
                'You do not have the necessary rights to update this study case')

        with app.app_context():
            source_study_case = StudyCase.query.filter(StudyCase.id == study_id).first()

        new_study_case = create_empty_study_case(user.id, study_name, source_study_case.repository,
                                                 source_study_case.process, group_id, study_id, StudyCase.FROM_STUDYCASE, 
                                                 flavor, source_study_case.execution_pod_flavor)

        copy_study_case = copy_study(source_study_case.id, new_study_case.id, user.id)

        response = make_response(jsonify(copy_study_case), 200)
        return response
    else:
        raise BadRequest('Missing mandatory parameter: study_id in url')


@app.route(f'/api/data/study-case/<int:study_id>/update-execution-flavor', methods=['POST'])
@auth_required
def update_study_case_execution_flavor(study_id):
    if study_id is not None:
        # Checking if user can access study data
        user = session['user']
        flavor = request.json.get('flavor', None)

        # Verify user has study case authorisation to update study (Manager)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(AccessRights.MANAGER, study_id):
            raise BadRequest(
                'You do not have the necessary rights to update this study case')

        response = make_response(jsonify(edit_study_execution_flavor(study_id, flavor)), 200)
        return response
    else:
        raise BadRequest('Missing mandatory parameter: study_id in url')


@app.route(f'/api/data/study-case/<int:study_id>/get-execution-flavor', methods=['GET'])
@auth_required
def get_study_case_execution_flavor(study_id):
    if study_id is not None:
        # Checking if user can access study data
        user = session['user']
        # Verify user has study case authorisation to update study (Manager)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(AccessRights.MANAGER, study_id):
            raise BadRequest(
                'You do not have the necessary rights to update this study case')

        response = make_response(jsonify(get_study_execution_flavor(study_id)), 200)
        return response
    else:
        raise BadRequest('Missing mandatory parameter: study_id in url')




@app.route(f'/api/data/study-case/<int:study_id>/edit', methods=['POST'])
@auth_required
def update_study_cases(study_id):

    if study_id is not None:
        # Checking if user can access study data
        user = session['user']

        group_id = request.json.get('group_id', None)
        study_name = request.json.get('new_study_name', None)
        flavor = request.json.get('flavor', None)

        # Verify user has study case authorisation to update study (Manager)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(AccessRights.MANAGER, study_id):
            raise BadRequest(
                'You do not have the necessary rights to update this study case')

        response = make_response(jsonify(edit_study(study_id, group_id, study_name, user.id, flavor)), 200)
        return response
    else:
        raise BadRequest('Missing mandatory parameter: study_id in url')


@app.route(f'/api/data/study-case/delete', methods=['DELETE'])
@auth_required
def delete_study_cases():
    user = session['user']
    studies = request.json.get('studies')

    if studies is not None:
        study_case_access = StudyCaseAccess(user.id)
        # Checking if user can access study data
        for study_id in studies:
            # Verify user has study case authorisation to delete study
            # (Manager)
            if not study_case_access.check_user_right_for_study(AccessRights.MANAGER, study_id):
                raise BadRequest(
                    'You do not have the necessary rights to delete this study case')

        # Proceeding after rights verification
        resp = make_response(
            jsonify(delete_study_cases_and_allocation(studies)), 200)
        return resp

    raise BadRequest(
        'Missing mandatory parameter: study identifier in url')


@app.route(f'/api/data/study-case/<int:study_id>/parameter/change', methods=['POST'])
@auth_required
def get_study_parameter_change_file_by_study_case_id(study_id):
    if study_id is not None:

        # Checking if user can access study data
        user = session['user']
        # Verify user has study case authorisation to load study (Commenter)
        study_case_access = StudyCaseAccess(user.id, study_id)
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


@app.route(f'/api/data/study-case/<int:study_id>/notifications', methods=['GET'])
@auth_required
def study_case_notifications(study_id):
    if request.method == 'GET':
        # Checking if user can access study data
        user = session['user']
        # Verify user has study case authorisation to get study notifications
        # (Commenter at least)
        study_case_access = StudyCaseAccess(user.id, study_id)
        results = []
        if study_case_access.check_user_right_for_study(AccessRights.COMMENTER, study_id):
            results = get_study_case_notifications(study_id)

        # Proceeding after rights verification
        resp = make_response(jsonify(results), 200)
        return resp


@app.route(f'/api/data/study-case/process', methods=['POST'])
@auth_required
def get_user_authorized_process_studies():
    # Checking if user can access study data
    user = session['user']
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


@app.route(f'/api/data/study-case/logs/<int:study_case_id>', methods=['GET'])
@auth_required
def get_study_case_logs(study_case_id):
    if study_case_id is not None:
        # Checking if user can access study data
        user = session['user']

        # Verify user has study case authorisation to retrieve execution logs
        # of study (RESTRICTED_VIEWER)
        study_case_access = StudyCaseAccess(user.id, study_case_id)
        if not study_case_access.check_user_right_for_study(AccessRights.RESTRICTED_VIEWER, study_case_id):
            raise BadRequest(
                'You do not have the necessary rights to retrieve execution logs of this study case')

        # Proceeding after rights verification
        resp = make_response(jsonify(study_case_logs(study_case_id)), 200)
        return resp

    raise BadRequest('Missing mandatory parameter: study identifier in url')


@app.route(f'/api/data/study-case/raw-logs/download', methods=['POST'])
@auth_required
def get_study_case_raw_logs_download():
    study_id = request.json.get('studyid', None)

    if study_id is None:
        raise BadRequest('Missing mandatory parameter: study_id')
    file_path = get_raw_logs(study_id)
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
        user = session['user']

        # Verify user has study case authorisation to load study (Restricted
        # viewer)
        study_case_access = StudyCaseAccess(user.id, study_id)
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
        user = session['user']
        # Verify user has study case authorisation to load study (Contributor)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(AccessRights.CONTRIBUTOR, study_id):
            raise BadRequest(
                'You do not have the necessary rights to claim study case execution right')

        # Proceeding after rights verification
        resp = make_response(jsonify(set_user_authorized_execution(study_id, user.id)), 200)
        return resp
    raise BadRequest('Missing mandatory parameter: study identifier in url')


@app.route(f'/api/data/study-case/favorite', methods=['POST'])
@auth_required
def favorite_study():
    # Checking if user can access study data
    user = session['user']
    study_id = request.json.get('study_id', None)
    if study_id is None:
        raise BadRequest('Missing mandatory parameter: study_id')

    add_favorite_study_case(study_id, user.id)

    # Get the study-case thanks to study_id into UserFavoriteStudy
    study_case = StudyCase.query \
        .filter(StudyCase.id == study_id) \
        .filter(UserStudyFavorite.study_case_id == study_id).first()

    resp = make_response(jsonify(
        f'The study, {study_case.name}, has been added in favorite study'), 200
    )

    return resp


@app.route(f'/api/data/study-case/<int:study_id>/favorite', methods=['DELETE'])
@auth_required
def delete_favorite_study(study_id):
    # Checking if user can access study data
    user = session['user']

    if study_id is None:
        raise BadRequest('Missing mandatory parameter: study_id')

    response = make_response(jsonify(remove_favorite_study_case(study_id, user.id)), 200)
    return response
