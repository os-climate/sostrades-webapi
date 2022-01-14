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
from flask import jsonify, make_response
from sos_trades_api.base_server import app
from sos_trades_api.tools.authentication.authentication import auth_required, get_authenticated_user
from sos_trades_api.controllers.sostrades_data.process_controller import api_get_processes_list, ProcessError


@app.route(f'/api/data/resources/process', methods=['GET'])
@auth_required
def processes_from_execution_engine():

    app.logger.info(get_authenticated_user())
    user = get_authenticated_user()
    try:
        # Retrieve process list available for current user
        processes = api_get_processes_list(user.id)
    except Exception as error:
        raise ProcessError(
            f'The following error occurs when trying to retrieve processes list : {str(error)}')

    resp = make_response(jsonify(processes), 200)
    return resp
