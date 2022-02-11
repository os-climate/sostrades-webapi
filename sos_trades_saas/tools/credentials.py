# -*- coding: utf-8 -*-
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

from functools import wraps
from flask import abort

from sos_trades_api.models.database_models import AccessRights
from sos_trades_api.tools.authentication.authentication import get_authenticated_user, AccessDenied
from sos_trades_api.tools.right_management.functional.study_case_access_right import StudyCaseAccess


def restricted_viewer_required(func):
    """
    View decorator - require restricted access to study
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:

            study_id = kwargs.get("study_id")

            # Checking if user can access study data
            user = get_authenticated_user()
            # Verify user has study case authorisation to retrieve execution status
            # of study (RESTRICTED_VIEWER)
            study_case_access = StudyCaseAccess(user.id)

            if not study_case_access.check_user_right_for_study(AccessRights.RESTRICTED_VIEWER, study_id):
                raise AccessDenied('You do not have the necessary rights to access this study case')

            return func(*args, **kwargs)

        except Exception as e:
            abort(403, str(e))

    return wrapper
