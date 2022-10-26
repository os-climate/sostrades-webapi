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
from flask import request, jsonify, make_response
from werkzeug.exceptions import BadRequest

from sos_trades_api.models.database_models import AccessRights
from sos_trades_api.server.base_server import app
from sos_trades_api.tools.authentication.authentication import auth_required, get_authenticated_user
from sos_trades_api.controllers.sostrades_post_processing.post_processing_controller import load_post_processing,\
    load_post_processing_graph_filters
from sos_trades_api.tools.right_management.functional.study_case_access_right import StudyCaseAccess
from sostrades_core.tools.post_processing.charts.chart_filter import ChartFilter


@app.route(f'/api/post-processing/study-case/<int:study_id>/post-processing', methods=['POST'])
@auth_required
def get_post_processing(study_id):

    if study_id is not None:
        # Checking if user can access study data
        user = get_authenticated_user()
        # Verify user has study case authorisation to retrieve study post
        # processing (RESTRICTED_VIEWER)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(AccessRights.RESTRICTED_VIEWER, study_id):
            raise BadRequest(
                'You do not have the necessary rights to retrieve this study case post processing')

        # Proceeding after rights verification
        if request.method == 'POST':

            # filters is not a mandatory parameter
            filters = request.json.get('filters', None)

            # Discipline key is a mandatory parameter
            discipline_key = request.json.get('discipline_key', None)

            # Module key is not a mandatory parameter
            module_name = request.json.get('module_name', '')

            missing_parameter = []
            if discipline_key is None:
                missing_parameter.append(
                    'Missing mandatory parameter: discipline_key')

            if len(missing_parameter) > 0:
                return BadRequest('\n'.join(missing_parameter))

            object_filters = None

            if filters is not None:
                object_filters = []
                for filter in filters:
                    object_filter = ChartFilter.from_dict(filter)
                    object_filters.append(object_filter)

            resp = make_response(
                jsonify(load_post_processing(study_id, discipline_key, object_filters, module_name)), 200)
            return resp

    raise BadRequest('Missing mandatory parameter: study identifier in url')


@app.route(f'/api/post-processing/study-case/<int:study_id>/filter/by/discipline', methods=['POST'])
@auth_required
def get_post_processing_filter(study_id):

    discipline_key = request.json.get('discipline_key', None)

    missing_parameter = []
    if discipline_key is None:
        missing_parameter.append(
            'Missing mandatory parameter: discipline_key')

    if len(missing_parameter) > 0:
        return BadRequest('\n'.join(missing_parameter))

    # Checking if user can access study data
    user = get_authenticated_user()
    # Verify user has study case authorisation to retrieve study post
    # processing filters (RESTRICTED_VIEWER)
    study_case_access = StudyCaseAccess(user.id, study_id)
    if not study_case_access.check_user_right_for_study(AccessRights.RESTRICTED_VIEWER, study_id):
        raise BadRequest(
            'You do not have the necessary rights to retrieve this study case post processing filters')

    # Proceeding after rights verification
    resp = make_response(
        jsonify(load_post_processing_graph_filters(study_id, discipline_key)), 200)
    return resp
