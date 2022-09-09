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

from flask import request, jsonify, make_response, abort, render_template
import plotly.graph_objects as go

from sos_trades_api.controllers.sostrades_main.study_case_controller import light_load_study_case
from sos_trades_api.models.database_models import AccessRights
from sos_trades_api.server.base_server import app
from sos_trades_api.tools.authentication.authentication import api_key_required, has_user_access_right
from sos_trades_core.tools.post_processing.post_processing_factory import PostProcessingFactory


@app.route(f'/api/v0/post-processing/<int:study_id>', methods=['GET'])
@api_key_required
@has_user_access_right(AccessRights.RESTRICTED_VIEWER)
def get_post_processing(study_id: int, ):
    """
    Return dictionary containing post processing  data

    :return: json response like
        {
            'discipline1': {'processing1 data'},
            'discipline2': {'processing2 data'}...
        }
    """
    try:

        study_manager = light_load_study_case(study_id)
        post_processing_factory = PostProcessingFactory()

        all_post_processing_bundle = post_processing_factory.get_all_post_processings(
            study_manager.execution_engine,
            filters_only=False)

        payload = {
           disc_name: disc_val.post_processings
           for disc_name, disc_values in all_post_processing_bundle.items()
           for disc_val in disc_values
        }

        return make_response(jsonify(payload), 200)

    except Exception as e:
        abort(400, str(e))


@app.route(f'/api/v0/post-processing/<int:study_id>/html', methods=['GET'])
@api_key_required
@has_user_access_right(AccessRights.RESTRICTED_VIEWER)
def get_post_processing_html(study_id: int):
    """
    Return html graph for post processing  data

    :return: html template
    """
    try:

        study_manager = light_load_study_case(study_id)
        post_processing_factory = PostProcessingFactory()

        all_post_processing_bundle = post_processing_factory.get_all_post_processings(
            study_manager.execution_engine,
            filters_only=False)

        graphs_dict = {}
        for discipline_name, discipline_values in all_post_processing_bundle.items():
            discipline_figs = []
            for discipline_value in discipline_values:
                post_processing_figs = []
                for post_processing in discipline_value.post_processings:
                    try:
                        post_processing_figs.append(go.Figure(post_processing).to_html(full_html=False, include_plotlyjs='cdn'))
                    except Exception:
                        app.logger.exception('Error on post processing to html')

                discipline_figs.append(post_processing_figs)

            graphs_dict[discipline_name] = discipline_figs

        payload = {
            "study_id": study_id,
            "study_name": study_manager.study.name,
            "graphs_dict": graphs_dict,
        }
        return render_template("post_process_plot.html", data=payload)

    except Exception as e:
        abort(400, str(e))