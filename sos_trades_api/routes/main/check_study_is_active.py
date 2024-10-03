'''
Copyright 2024 Capgemini

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

from flask import jsonify, make_response

from sos_trades_api.controllers.sostrades_main.study_case_controller import (
    check_study_is_still_active_or_kill_pod,
)
from sos_trades_api.server.base_server import app
from sos_trades_api.tools.authentication.authentication import local_only


@app.route("/api/main/check-study-is-active", methods=["GET"])
@local_only
def check_study_is_active():
    '''
    check if the study is active, if not, kill study pod
    This function is only accessible by local remote adress
    '''
    check_study_is_still_active_or_kill_pod()
    return make_response(jsonify("study is active"), 200)
