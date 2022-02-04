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

from flask import Response, request, make_response, jsonify, abort

from sos_trades_api.controllers.sostrades_main.study_case_controller import load_study_case

from sos_trades_api.base_server import app, study_case_cache

# TODO user / group credentials


@app.route(f'/saas/study-case-link/<int:study_id>', methods=['GET'])
def get_study_case_link(study_id: int):
    """
    Return study-case web-GUI url

    @return: json response like {'study-link': 'http/link/to/webgui/'}
    """

    if request.method == "GET":

        study_url = ""
        msg = ""
        status_code = 200

        try:
            study_case_cache.get_study_case(study_id, False)
            study_url = f'{app.config.get("SOS_TRADES_FRONT_END_DNS", "")}study/{study_id}'

        except Exception as e:
            msg = str(e)
            status_code = 400

        finally:
            payload = {
                "study_url": study_url,
                "message": msg
            }

        return make_response(jsonify(payload), status_code)

    abort(405)

