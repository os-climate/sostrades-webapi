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
from flask import jsonify, make_response, request, session
from werkzeug.exceptions import BadRequest

from sos_trades_api.controllers.sostrades_data.entity_right_controller import (
    apply_entities_changes,
    get_group_entities_rights,
    get_process_entities_rights,
    get_study_case_entities_rights,
)
from sos_trades_api.server.base_server import app
from sos_trades_api.tools.authentication.authentication import (
    auth_required,
    get_authenticated_user,
)


@app.route("/api/data/entity-right", methods=["POST"])
@auth_required
def change_entities_rights():

    app.logger.info(get_authenticated_user())
    user = get_authenticated_user()

    entity_rights = request.json.get("entity_rights", None)

    if entity_rights is None:
        raise BadRequest("Missing mandatory parameter: entity_rights")

    resp = make_response(
        jsonify(apply_entities_changes(user.id, user.user_profile_id, entity_rights)), 200)
    return resp


@app.route("/api/data/entity-right/study-case/<int:study_id>", methods=["GET"])
@auth_required
def study_case_entities_rights(study_id):

    app.logger.info(get_authenticated_user())
    user = get_authenticated_user()

    resp = make_response(
        jsonify(get_study_case_entities_rights(user.id, study_id)), 200)
    return resp


@app.route("/api/data/entity-right/process/<int:process_id>", methods=["GET"])
@auth_required
def process_entities_rights(process_id):

    user = session["user"]
    app.logger.info(user)

    resp = make_response(
        jsonify(get_process_entities_rights(user.id, user.user_profile_id, process_id)), 200)
    return resp


@app.route("/api/data/entity-right/group/<int:group_id>", methods=["GET"])
@auth_required
def group_entities_rights(group_id):

    app.logger.info(get_authenticated_user())
    user = get_authenticated_user()

    resp = make_response(
        jsonify(get_group_entities_rights(user.id, group_id)), 200)
    return resp
