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
from sos_trades_api.server.base_server import app
from sos_trades_api.models.loaded_study_case import LoadStatus
from sos_trades_api.controllers.sostrades_post_processing.post_processing_controller import \
    reset_study_from_cache_and_light_load
from sos_trades_api.tools.authentication.authentication import auth_required, get_authenticated_user
from sos_trades_api.tools.right_management.functional.study_case_access_right import StudyCaseAccess
from sos_trades_api.models.database_models import AccessRights
from werkzeug.exceptions import BadRequest
from sos_trades_api.controllers.sostrades_main.study_case_controller import light_load_study_case
from flask import abort, jsonify, make_response


@app.route(f'/api/post-processing/study-case/<int:study_id>', methods=['GET'])
@auth_required
def post_processing_load_study_case_by_id(study_id):
    if study_id is not None:

        # Checking if user can access study data
        user = get_authenticated_user()

        # Verify user has study case authorisation to load study (Restricted
        # viewer)
        study_case_access = StudyCaseAccess(user.id)
        if not study_case_access.check_user_right_for_study(AccessRights.RESTRICTED_VIEWER, study_id):
            raise BadRequest(
                'You do not have the necessary rights to load this study case')
        study_access_right = study_case_access.get_user_right_for_study(
            study_id)
        # set the study case in the cache
        study_manager = light_load_study_case(study_id)
        if study_manager is None:
            resp = make_response(
                jsonify(True), 200)
        else:
            if study_manager.load_status == LoadStatus.IN_ERROR:
                app.logger.info("study manager has error")
            resp = make_response(
                jsonify(study_manager.load_status == LoadStatus.LOADED or study_manager.load_status == LoadStatus.IN_ERROR), 200)

        return resp

    abort(403)


@app.route(f'/api/post-processing/study-case/<int:study_id>/reset-cache', methods=['GET'])
@auth_required
def reset_study_from_cache_(study_id):
    if study_id is not None:

        # Checking if user can access study data
        user = get_authenticated_user()

        # Verify user has study case authorisation to load study (Restricted
        # viewer)
        study_case_access = StudyCaseAccess(user.id)
        if not study_case_access.check_user_right_for_study(AccessRights.RESTRICTED_VIEWER, study_id):
            raise BadRequest(
                'You do not have the necessary rights to load this study case')
        study_access_right = study_case_access.get_user_right_for_study(
            study_id)
        # set the study case in the cache

        study_manager = reset_study_from_cache_and_light_load(study_id)
        if study_manager is None:
            resp = make_response(
                jsonify(True), 200)
        else:
            if study_manager.load_status == LoadStatus.IN_ERROR:
                app.logger.info("study manager has error")
            resp = make_response(
                jsonify(study_manager.load_status == LoadStatus.LOADED or study_manager.load_status == LoadStatus.IN_ERROR), 200)

        return resp

    abort(403)


@app.route(f'/api/post-processing/study-case/<int:study_id>/reload', methods=['GET'])
@auth_required
def reload_study_case_by_id(study_id):
    if study_id is not None:

        # Checking if user can access study data
        user = get_authenticated_user()

        # Verify user has study case authorisation to load study (Restricted
        # viewer)
        study_case_access = StudyCaseAccess(user.id)
        if not study_case_access.check_user_right_for_study(AccessRights.RESTRICTED_VIEWER, study_id):
            raise BadRequest(
                'You do not have the necessary rights to load this study case')
        study_access_right = study_case_access.get_user_right_for_study(
            study_id)
        # set the study case in the cache
        study_manager = light_load_study_case(study_id, True)
        if study_manager is None:
            resp = make_response(
                jsonify(True), 200)
        else:
            if study_manager.load_status == LoadStatus.IN_ERROR:
                app.logger.info("study manager has error")
            resp = make_response(
                jsonify(study_manager.load_status == LoadStatus.LOADED or study_manager.load_status == LoadStatus.IN_ERROR), 200)

        return resp

    abort(403)
