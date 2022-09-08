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
# coding: utf-8
from flask import jsonify, make_response, session
from sos_trades_api.server.base_server import app
from sos_trades_api.tools.authentication.authentication import auth_required, study_manager_profile
from sos_trades_api.controllers.sostrades_data.process_controller import api_get_processes_for_user, ProcessError, api_get_processes_for_dashboard


@app.route(f'/api/data/resources/process', methods=['GET'])
@auth_required
def get_processes_for_user():

    user = session['user']
    app.logger.info(user)

    try:
        # Retrieve process list available for current user
        processes = api_get_processes_for_user(user)
    except Exception as error:
        raise ProcessError(
            f'The following error occurs when trying to retrieve processes list : {str(error)}')

    resp = make_response(jsonify(processes), 200)
    return resp


@app.route(f'/api/data/resources/process/dashboard', methods=['GET'])
@auth_required
@study_manager_profile
def get_processes_for_dashboard():

    user = session['user']
    app.logger.info(user)

    try:
        processes = api_get_processes_for_dashboard()
    except Exception as error:
        raise ProcessError(
            f'The following error occurs when trying to retrieve processes list : {str(error)}')

    resp = make_response(jsonify(processes), 200)
    return resp
