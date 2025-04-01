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
from flask import jsonify, make_response, session
from werkzeug.exceptions import BadRequest
from sos_trades_api.controllers.sostrades_data.study_stand_alone_controller import get_status_export_study_stand_alone, start_export_study_stand_alone
from sos_trades_api.server.base_server import Config, app
from sos_trades_api.tools.authentication.authentication import auth_required
from sos_trades_api.models.database_models import (
    AccessRights
)
from sos_trades_api.tools.right_management.functional.study_case_access_right import (
    StudyCaseAccess,
)

@app.route("/api/data/study-stand-alone/<int:study_id>/export/start", methods=["POST"])
@auth_required
def start_export_study_in_stand_alone(study_id):
    """
    start the export of study in stand alone
    """
    if study_id is not None:
        user = session["user"]
        # Verify user has study case authorisation to load study (Commenter)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(AccessRights.RESTRICTED_VIEWER, study_id):
            raise BadRequest(
                "You do not have the necessary rights to retrieve this information about this study case")
    return make_response(jsonify(start_export_study_stand_alone(study_id)), 200)

@app.route("/api/data/study-stand-alone/<int:study_id>/export/status", methods=["GET"])
@auth_required
def get_export_study_in_stand_alone_status(study_id):
    """
    get the status of the export study in stand alone
    """
    if study_id is not None:
        user = session["user"]
        # Verify user has study case authorisation to load study (Commenter)
        study_case_access = StudyCaseAccess(user.id, study_id)
        if not study_case_access.check_user_right_for_study(AccessRights.RESTRICTED_VIEWER, study_id):
            raise BadRequest(
                "You do not have the necessary rights to retrieve this information about this study case")
    return make_response(jsonify(get_status_export_study_stand_alone(study_id)), 200)

@app.route("/api/data/study-stand-alone/<int:study_id>/export/download", methods=["GET"])
@auth_required
def download_export_study_in_stand_alone(study_id):
    """
    download the study in stand alone in a zip file
    """
   
    return make_response(jsonify(study_id), 200)
