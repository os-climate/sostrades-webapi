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

import time
from flask import request, make_response, jsonify, abort

from sos_trades_api.controllers.sostrades_data.calculation_controller import calculation_status
from sos_trades_api.controllers.sostrades_data.authentication_controller import authenticate_user_standard
from sos_trades_api.models.database_models import AccessRights
from sos_trades_api.tools.authentication.authentication import AuthenticationError, auth_required,\
    get_authenticated_user
from sos_trades_api.tools.right_management.functional.study_case_access_right import StudyCaseAccess
from sos_trades_api.controllers.sostrades_main.study_case_controller import light_load_study_case, load_study_case
from sos_trades_saas.controller.saas_module_controller import filter_tree_node_data, filter_children_data

from sos_trades_api.base_server import app, study_case_cache
from sos_trades_saas.tools.credentials import restricted_viewer_required


@app.route(f'/saas/login', methods=['POST'])
def login():
    """
    Return bearer access token

    @return: json response like {'access_token': access_token}
    """

    if request.json is None:
        abort(400, "'username' and 'password' not found in request")

    elif request.json.get('username') is None:
        abort(400, "'username' not found in request")

    elif request.json.get('password') is None:
        abort(400, "'password' not found in request")

    try:
        username = request.json.get('username')
        password = request.json.get('password')

        access_token, _, _, _ = authenticate_user_standard(username, password)

        return make_response(jsonify({'access_token': access_token}), 200)

    except AuthenticationError as error:
        abort(403, str(error))

    except Exception as err:
        abort(400, str(err))


@app.route(f'/saas/study-case-link/<int:study_id>', methods=['GET'])
@auth_required
def get_study_case_link(study_id: int):
    """
    Return study-case web-GUI url

    @return: json response like {'study-link': 'http/link/to/webgui/'}
    """

    if request.method == "GET":

        try:

            study_case_cache.get_study_case(study_id, False)
            study_url = f'{app.config.get("SOS_TRADES_FRONT_END_DNS", "")}study/{study_id}'

            return make_response(jsonify({"study_url": study_url}), 200)

        except Exception as e:
            abort(400, str(e))

    abort(405)


@app.route(f'/saas/load-study-case/<int:study_id>', methods=['GET'])
@app.route(f'/saas/load-study-case/<int:study_id>/<int:timeout>', methods=['GET'])
@auth_required
@restricted_viewer_required
def load_study(study_id: int, timeout: int = 30):
    """
    Return dictionary instance containing loaded study
    :rtype: dict
    :return: dictionary like:
        {
            'study_name': 'this is 'study_id name',
            'tree_node': 'this contains filtered 'treenode' data
        }
    """

    if request.method == "GET":
        try:

            user = get_authenticated_user()
            study_case_access = StudyCaseAccess(user.id)
            study_access_right = study_case_access.get_user_right_for_study(study_id)

            load_study_case(study_id, study_access_right, user.id)
            for _ in range(timeout):

                study_manager = light_load_study_case(study_id)

                if not study_manager.loaded:
                    time.sleep(3)
                else:
                    break

            loaded_study = load_study_case(study_id, study_access_right, user.id)

            tree_node = loaded_study.treenode
            # TODO pas robuste si treenode vide

            payload = {
                "study_name": loaded_study.study_case.name,
                "tree_node": {
                    "data": filter_tree_node_data(tree_node=tree_node),
                    "children": filter_children_data(tree_node=tree_node)
                }
            }

            return make_response(jsonify(payload), 200)

        except Exception as e:
            abort(400, str(e))

    abort(405)


@app.route(f'/saas/monitor/study-case/<int:study_id>', methods=['GET'])
@auth_required
@restricted_viewer_required
def monitor_study_execution(study_id: int):
    try:

        return make_response(jsonify(calculation_status(study_id)), 200)

    except Exception as e:
        abort(400, str(e))

