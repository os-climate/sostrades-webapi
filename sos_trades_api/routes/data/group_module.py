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

from sos_trades_api.controllers.sostrades_data.group_controller import (
    create_group,
    delete_group,
    edit_group,
    get_all_groups,
    get_group_list,
)
from sos_trades_api.models.database_models import AccessRights
from sos_trades_api.server.base_server import app
from sos_trades_api.tools.authentication.authentication import (
    auth_required,
    get_authenticated_user,
)
from sos_trades_api.tools.right_management.functional.group_access_right import (
    GroupAccess,
)


@app.route("/api/data/group", methods=["GET", "POST", "DELETE"])
@auth_required
def groups():
    if request.method == "GET":
        resp = make_response(jsonify(get_all_groups()), 200)
        return resp

    elif request.method == "POST":
        app.logger.info(get_authenticated_user())
        user = session["user"]
        name = request.json.get("name", None)
        description = request.json.get("description", None)
        confidential = request.json.get("confidential", None)

        missing_parameter = []
        if name is None:
            missing_parameter.append("Missing mandatory parameter: name")
        if description is None:
            missing_parameter.append(
                "Missing mandatory parameter: description")
        if confidential is None:
            missing_parameter.append(
                "Missing mandatory parameter: confidential")

        if len(missing_parameter) > 0:
            raise BadRequest("\n".join(missing_parameter))

        resp = make_response(jsonify(create_group(
            user.id, name, description, confidential)), 200)
        return resp

    elif request.method == "DELETE":
        group_id = request.json.get("group_id", None)

        if group_id is None:
            raise BadRequest("Missing mandatory parameter: groupId")

        # Checking if user can access group data
        user = session["user"]

        # Verify user has group authorisation to delete group (MANAGER)
        group_access = GroupAccess(user.id)
        if not group_access.check_user_right_for_group(AccessRights.MANAGER, group_id):
            raise BadRequest("You do not have the necessary rights to delete this group")

        # Proceeding after rights verification
        resp = make_response(jsonify(delete_group(group_id)), 200)
        return resp


@app.route("/api/data/group/user", methods=["GET"])
@auth_required
def group():
    if request.method == "GET":
        app.logger.info(get_authenticated_user())
        user = session["user"]
        resp = make_response(jsonify(get_group_list(user.id)), 200)
        return resp


@app.route("/api/data/group/<int:group_id>", methods=["POST"])
@auth_required
def update_group(group_id):

    user = session["user"]

    if group_id is None or group_id <= 0:
        raise BadRequest(
            f"Invalid argument value for group_id.\nReceived {group_id}, expected strictly positive integer")

    group_id = request.json.get("id", None)
    name = request.json.get("name", None)
    description = request.json.get("description", None)

    missing_parameter = []
    if name is None or len(name) == 0:
        missing_parameter.append("Missing mandatory parameter: name")

    if description is None or len(description) == 0:
        missing_parameter.append("Missing mandatory parameter: description")

    if len(missing_parameter) > 0:
        raise BadRequest(missing_parameter)

    if len(missing_parameter) > 0:
        raise BadRequest(missing_parameter)

    resp = make_response(jsonify(edit_group(group_id, name, description, user.id)), 200)
    return resp


