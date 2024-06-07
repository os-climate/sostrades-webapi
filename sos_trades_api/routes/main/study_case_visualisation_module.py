'''
Copyright 2022 Airbus SAS
Modifications on 2024/06/07 Copyright 2024 Capgemini
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
from flask import jsonify, make_response, session
from werkzeug.exceptions import BadRequest

from sos_trades_api.controllers.sostrades_main.visualisation_controller import (
    get_execution_sequence_graph_data,
    get_interface_diagram_data,
    get_n2_diagram_graph_data,
)
from sos_trades_api.models.database_models import AccessRights
from sos_trades_api.server.base_server import app
from sos_trades_api.tools.authentication.authentication import auth_required
from sos_trades_api.tools.right_management.functional.study_case_access_right import (
    StudyCaseAccess,
)


@app.route('/api/main/study-case/<int:study_id>/execution-sequence', methods=['GET'])
@auth_required
def execution_sequence_graph_data(study_id):
    if study_id is not None:

        user = session['user']

        # Verify user has study case authorisation to retrieve execution status of study (RESTRICTED_VIEWER)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(
            AccessRights.RESTRICTED_VIEWER, study_id
        ):
            raise BadRequest(
                'You do not have the necessary rights to retrieve '
                'execution sequence data of this study case'
            )

        # Proceed after rights verification
        resp = make_response(jsonify(get_execution_sequence_graph_data(study_id)), 200)
        return resp

    raise BadRequest('Missing mandatory parameter: study identifier in url')

@app.route('/api/main/study-case/<int:study_id>/interface-diagram', methods=['GET'])
@auth_required
def interface_diagram_data(study_id):
    if study_id is not None:

        user = session['user']

        # Verify user has study case authorisation to retrieve execution status of study (RESTRICTED_VIEWER)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(
            AccessRights.RESTRICTED_VIEWER, study_id
        ):
            raise BadRequest(
                'You do not have the necessary rights to retrieve '
                'interface diagram of this study case'
            )

        # Proceed after rights verification
        resp = make_response(jsonify(get_interface_diagram_data(study_id)), 200)
        return resp

    raise BadRequest('Missing mandatory parameter: study identifier in url')


@app.route('/api/main/study-case/<int:study_id>/n2-diagram', methods=['GET'])
@auth_required
def n2_diagram_graph_data(study_id):

    if study_id is not None:

        user = session['user']

        # Verify user has study case authorisation to load study (Restricted
        # viewer)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(
            AccessRights.RESTRICTED_VIEWER, study_id
        ):
            raise BadRequest(
                'You do not have the necessary rights to retrieve n2 diagram data of this study case'
            )

        # Proceed after rights verification
        resp = make_response(jsonify(get_n2_diagram_graph_data(study_id)), 200)

        return resp

    raise BadRequest('Missing mandatory parameter: study identifier in url')
