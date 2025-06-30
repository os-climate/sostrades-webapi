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
from flask import Blueprint, request, send_file, session
from werkzeug.exceptions import BadRequest

from sos_trades_api.models.database_models import AccessRights
from sos_trades_api.tools.right_management.functional.study_case_access_right import (
    StudyCaseAccess,
)
from sos_trades_api.tools.study_management.study_management import get_file_stream

parameter_blueprint = Blueprint('parameter', __name__)

def init_parameter_routes(decorator):
    """
    Initialize study case read only routes with a given decorator
    """
       
    @parameter_blueprint.route("/<int:study_id>/parameter/download", methods=["POST"])
    @decorator
    def get_study_parameter_file_by_study_case_id(study_id):
        if study_id is not None:

            user = session["user"]
            # Verify user has study case authorisation to load study (Commenter)
            study_case_access = StudyCaseAccess(user.id, study_id)
            if not study_case_access.check_user_right_for_study(AccessRights.COMMENTER, study_id):
                raise BadRequest(
                    "You do not have the necessary rights to retrieve this information about study case")

            # Proceeding after rights verification
            parameter_key = request.json.get("parameter_key", None)

            if parameter_key is None:
                raise BadRequest("Missing mandatory parameter: parameter_key")

            resp = send_file(get_file_stream(study_id, parameter_key), mimetype="arrayBuffer")
            return resp

        raise BadRequest("Missing mandatory parameter: study identifier in url")
