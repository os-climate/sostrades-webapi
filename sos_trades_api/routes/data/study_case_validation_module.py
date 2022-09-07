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
from flask import request, jsonify, make_response

from werkzeug.exceptions import BadRequest
from sos_trades_api.models.database_models import AccessRights
from sos_trades_api.server.base_server import app
from sos_trades_api.tools.authentication.authentication import auth_required, get_authenticated_user
from sos_trades_api.controllers.sostrades_data.study_case_validation_controller import get_study_case_validation_list,\
    add_study_case_validation
from sos_trades_api.tools.right_management.functional.study_case_access_right import StudyCaseAccess


@app.route(f'/api/data/study-case-validation/<int:study_id>', methods=['GET', 'POST'])
@auth_required
def study_case_validation(study_id):

    if request.method == 'GET':
        # Transform object array to json convertible
        result = [sc.serialize() for sc in get_study_case_validation_list(study_id)]
        resp = make_response(jsonify(result), 200)
        return resp

    elif request.method == 'POST':
        app.logger.info(get_authenticated_user())
        user = get_authenticated_user()
        namespace = request.json.get('namespace', None)
        status = request.json.get('status', None)
        comment = request.json.get('comment', None)

        # Verify user has study case authorisation to load study (Contributor)
        study_case_access = StudyCaseAccess(user.id)
        if not study_case_access.check_user_right_for_study(AccessRights.CONTRIBUTOR, study_id):
            raise BadRequest(
                'You do not have the necessary rights to copy this study case')

        # Proceed after right verification
        missing_parameter = []
        if namespace is None:
            missing_parameter.append('Missing mandatory parameter: namespace')

        if status is None:
            missing_parameter.append('Missing mandatory parameter: status')
        if comment is None:
            missing_parameter.append('Missing mandatory parameter: comment')

        if len(missing_parameter) > 0:
            raise BadRequest('\n'.join(missing_parameter))

        resp = make_response(jsonify(add_study_case_validation(study_id, user, namespace, status, comment)), 200)
        return resp
