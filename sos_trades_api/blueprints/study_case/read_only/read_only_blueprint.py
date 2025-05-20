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
from flask import Blueprint, send_file, session
from werkzeug.exceptions import BadRequest
from sos_trades_api.controllers.sostrades_data.study_case_controller import (
    add_last_opened_study_case,
)
from sos_trades_api.models.database_models import AccessRights
from sos_trades_api.tools.right_management.functional.study_case_access_right import (
    StudyCaseAccess,
)
from sos_trades_api.tools.study_management.study_management import (
    get_read_only_file_path,
)

read_only_blueprint = Blueprint('read-only', __name__)

def init_read_only_routes(decorator):
    """
    Initialize study case read only routes with a given decorator
    """
       
    @read_only_blueprint.route("/<int:study_id>/read-only-mode", methods=["GET"])
    @decorator
    def load_study_case_by_id_in_read_only(study_id):
        """
        Retreive the study in read only mode, return none if no read only mode found
        """
        if study_id is not None:
            user = session["user"]
            # Verify user has study case authorisation to load study (Commenter)
            study_case_access = StudyCaseAccess(user.id, study_id)
            if not study_case_access.check_user_right_for_study(AccessRights.RESTRICTED_VIEWER, study_id):
                raise BadRequest(
                    "You do not have the necessary rights to retrieve this information about this study case")
            study_access_right = study_case_access.get_user_right_for_study(
                study_id)

            loaded_study_json_path = get_read_only_file_path(study_id, False)
            # loaded_study_json = None
            # with open(loaded_study_json_path, 'r') as json_file:
            #     loaded_study_json = json.load(json_file)
            # Add this study in last study opened in database
            add_last_opened_study_case(study_id, user.id)
            return send_file(loaded_study_json_path)
        raise BadRequest("Missing mandatory parameter: study identifier in url")
