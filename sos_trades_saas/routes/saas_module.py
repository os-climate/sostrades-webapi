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

from flask import request, make_response, jsonify, abort

from sos_trades_api.controllers.sostrades_data.authentication_controller import authenticate_user_standard
from sos_trades_api.tools.authentication.authentication import AuthenticationError, auth_required
from sos_trades_api.controllers.sostrades_main.study_case_controller import light_load_study_case, load_study_case
from sos_trades_api.base_server import app, study_case_cache

# TODO user / group credentials
# TODO optional timeout on  *load_study*


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
def load_study(study_id: int, timeout: int = 30):
    """
    Return

    @return:
    """

    if request.method == "GET":

        msg = ""
        status_code = 200
        print(timeout)

        try:
            # do stuff here
            pass

        except Exception as e:

            msg = str(e)
            status_code = 400

        finally:
            payload = {
                "message": msg
            }

        return make_response(jsonify(payload), status_code)

    abort(405)
