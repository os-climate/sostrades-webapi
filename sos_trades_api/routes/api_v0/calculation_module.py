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

from flask import make_response, jsonify, abort, session

from sos_trades_api.controllers.sostrades_main.study_case_controller import light_load_study_case
from sos_trades_api.models.database_models import AccessRights
from sos_trades_api.server.base_server import app
from sos_trades_api.tools.authentication.authentication import api_key_required, has_user_access_right
from sos_trades_api.controllers.sostrades_data.calculation_controller import calculation_status, execute_calculation


@app.route(f'/api/v0/calculation/execute/<int:study_id>', methods=['POST'])
@api_key_required
@has_user_access_right(AccessRights.CONTRIBUTOR)
def study_case_execution(study_id: int):
    """
    Trigger calculation execution
    Return study-case discipline and execution status

    :return: json response like
        {
            'disciplines_status': {
                disc_1 : status,
                disc_2 : status...
            }
            "study_case_execution_cpu": val,
            "study_case_execution_memory": val,
            "study_case_execution_status": status,
            "study_case_id": study_id
        }
    """

    user = session['user']
    try:
        light_load_study_case(study_id)

        execute_calculation(study_id, user.username)

        return make_response(jsonify(calculation_status(study_id)), 200)

    except Exception as e:
        abort(400, str(e))


@app.route(f'/api/v0/calculation/status/<int:study_id>', methods=['GET'])
@api_key_required
@has_user_access_right(AccessRights.RESTRICTED_VIEWER)
def study_case_execution_status(study_id: int):
    """
    Return study-case discipline and execution status

    :return: json response like
        {
            'disciplines_status': {
                disc_1 : status,
                disc_2 : status...
            }
            "study_case_execution_cpu": val,
            "study_case_execution_memory": val,
            "study_case_execution_status": status,
            "study_case_id": study_id
        }
    """
    try:

        return make_response(jsonify(calculation_status(study_id)), 200)

    except Exception as e:
        abort(400, str(e))
