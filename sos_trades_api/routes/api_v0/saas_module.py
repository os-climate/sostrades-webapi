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
import plotly.graph_objects as go
from flask import request, make_response, jsonify, abort, render_template

from sos_trades_api.controllers.sostrades_data.calculation_controller import calculation_status
from sos_trades_api.controllers.sostrades_data.authentication_controller import authenticate_user_standard
from sos_trades_api.models.database_models import StudyCaseChange
from sos_trades_api.tools.authentication.authentication import AuthenticationError, auth_required,\
    get_authenticated_user
from sos_trades_api.tools.right_management.functional.study_case_access_right import StudyCaseAccess
from sos_trades_api.controllers.sostrades_main.study_case_controller import light_load_study_case, load_study_case, \
    update_study_parameters

from sos_trades_core.tools.post_processing.post_processing_factory import PostProcessingFactory

from sos_trades_api.base_server import app, study_case_cache
from sos_trades_api.tools.api_v0.credentials import restricted_viewer_required
from sos_trades_api.tools.api_v0.rendering_filter import filter_tree_node_data, filter_children_data


@app.route(f'/api/v0/login', methods=['POST'])
def login():
    """
    Return bearer access token

    :return: json response like {'access_token': access_token}
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


@app.route(f'/api/v0/study-url/<int:study_id>', methods=['GET'])
@auth_required
def get_study_case_url(study_id: int):
    """
    Return study-case web-GUI url

    :return: json response like {'study_url': 'http/link/to/webgui/'}
    """

    try:

        study_case_cache.get_study_case(study_id, False)
        study_url = f'{app.config.get("SOS_TRADES_FRONT_END_DNS", "")}study/{study_id}'

        return make_response(jsonify({"study_url": study_url}), 200)

    except Exception as e:
        abort(400, str(e))


@app.route(f'/api/v0/load/study/<int:study_id>', methods=['GET'])
@app.route(f'/api/v0/load/study/<int:study_id>/<int:timeout>', methods=['GET'])
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

    try:

        user = get_authenticated_user()
        study_case_access = StudyCaseAccess(user.id)
        study_access_right = study_case_access.get_user_right_for_study(study_id)

        # Trigger load
        load_study_case(study_id, study_access_right, user.id)

        for _ in range(timeout):

            study_manager = light_load_study_case(study_id)

            if study_manager.loaded:
                break
            else:
                time.sleep(1)

        loaded_study = load_study_case(study_id, study_access_right, user.id)
        tree_node = loaded_study.treenode

        # TODO pas robuste si treenode is {}

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


@app.route(f'/api/v0/monitor/study/<int:study_id>', methods=['GET'])
@auth_required
@restricted_viewer_required
def monitor_study_execution(study_id: int):
    try:

        return make_response(jsonify(calculation_status(study_id)), 200)

    except Exception as e:
        abort(400, str(e))


@app.route(f'/api/v0/post-process/html/<int:study_id>', methods=['GET'])
@auth_required
@restricted_viewer_required
def plotly_render(study_id: int):
    try:
        study_manager = light_load_study_case(study_id)
        post_processing_factory = PostProcessingFactory()

        complete_post_process = post_processing_factory.get_all_post_processings(
            study_manager.execution_engine,
            as_json=True,
            filters_only=False)

        graphs = {}

        for discipline_name, discipline_values in complete_post_process.items():

            graphs[discipline_name] = {}

            for index, discipline_value in enumerate(discipline_values):

                post_processings = discipline_value.post_processings
                figs = []

                for post_processing in post_processings:
                    fig = go.Figure(post_processing)
                    figs.append(fig.to_html(full_html=False, include_plotlyjs='cdn'))

                graphs[discipline_name].update({str(index): figs})

        payload = {
            "study_id": study_id,
            "graphs": graphs,
        }
        return render_template("post_process_plot.html", data=payload)
    except Exception as e:
        abort(400, str(e))


@app.route(f'/api/v0/post-process/<int:study_id>', methods=['GET'])
@auth_required
@restricted_viewer_required
def load_post_process(study_id: int):
    try:

        study_manager = light_load_study_case(study_id)
        post_processing_factory = PostProcessingFactory()

        # TODO : create a rendering module to filter json data

        all_post_processings_bundle = post_processing_factory.get_all_post_processings(
            study_manager.execution_engine,
            filters_only=False)

        lean_pp = {}
        for disc_name, disc_values in all_post_processings_bundle.items():
            for disc_val in disc_values:
                pps = disc_val.post_processings
                lean_pp[disc_name] = pps

        for disc_name, post_processings in lean_pp.items():
            lean_pp[disc_name] = [{k: v} for pp in pps for k, v in pp.items() if k == "data" or k == "csv_data"]

        return make_response(jsonify(lean_pp), 200)

    except Exception as e:
        abort(400, str(e))


@app.route(f'/api/v0/update/parameter/<int:study_id>', methods=['POST'])
@auth_required
@restricted_viewer_required
def update_study_case(study_id: int):
    # TODO update a list of params ?
    needed_params = ['variableId', 'newValue', 'oldValue', 'unit']
    if request.json is None:
        abort(400, "'" + ", ".join(needed_params) + "' parameters not found in request.")

    else:
        for param in needed_params:
            if request.json.get(param) is None:
                abort(400, "At least one of '" + ", ".join(needed_params) + "' parameter not found in request.")

    try:
        light_load_study_case(study_id)

        request.json["changeType"] = StudyCaseChange.SCALAR_CHANGE
        request.json["namespace"], request.json["var_name"] = tuple(request.json.get("variableId").rsplit('.', 1))
        params = [request.json]

        resp = update_study_parameters(study_id, get_authenticated_user(), None, None, params)

        return make_response(jsonify(resp), 200)
    except Exception as e:
        abort(400, str(e))

