'''
Copyright 2025 Capgemini

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

from sos_trades_api.controllers.sostrades_data.dashboard_controller import (
    get_study_dashboard_in_file,
    save_study_dashboard_in_file,
)
from sos_trades_api.models.database_models import AccessRights
from sos_trades_api.server.base_server import app
from sos_trades_api.tools.authentication.authentication import auth_required
from sos_trades_api.tools.right_management.functional.study_case_access_right import (
    StudyCaseAccess,
)


@app.route("/api/data/dashboard/<int:study_id>", methods=["GET"])
@auth_required
def get_dashboard_data(study_id):
    if study_id is not None:
        user = session["user"]

        # Verify user has study case authorisation to load study (Restricted viewer)
        study_case_access = StudyCaseAccess(user.id, study_id)

        if not study_case_access.check_user_right_for_study(AccessRights.RESTRICTED_VIEWER, study_id):
            raise BadRequest(
                "You do not have the necessary rights to load this study case")

        # Proceeding after rights verification
        return make_response(get_study_dashboard_in_file(study_id), 200)
    raise BadRequest("Missing mandatory parameter: study identifier in url")

@app.route("/api/data/dashboard/<int:study_id>", methods=["POST"])
@auth_required
def update_dashboard_data(study_id):
    if study_id is not None:
        user = session["user"]
        study_case_access = StudyCaseAccess(user.id, study_id)

        # Verify user has study case authorisation to modify study (contributor)
        if not study_case_access.check_user_right_for_study(AccessRights.CONTRIBUTOR, study_id):
            raise BadRequest(
                "You do not have the necessary rights to load this study case")

        # Proceeding after rights verification
        # Save dashboard data inside dashboard file
        app.logger.info("Updating dashboard data")
        request_json = request.get_json(force=True)
        save_study_dashboard_in_file(dashboard_data=request_json)
        return make_response(jsonify("Dashboard data saved in file"), 200)
    raise BadRequest("Missing mandatory parameter: study identifier in url")