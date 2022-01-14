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
"""
mode: python; py-indent-offset: 4; tab-width: 4; coding: utf-8
Study case validation Functions
"""
from sos_trades_api.base_server import db
from datetime import datetime, timezone
from sos_trades_api.models.database_models import StudyCaseValidation


def get_study_case_validation_list(study_case_id):
    """
    Ask database to retrieve all study case validation information

    List is filtered validation data

    :returns: sos_trades_api.models.database_models.StudyCaseValidation[]
    """
    sc_val_query = StudyCaseValidation.query.filter(StudyCaseValidation.study_case_id == study_case_id).\
        order_by(StudyCaseValidation.id.desc()).all()

    return sc_val_query


def add_study_case_validation(study_case_id, user, validation_type, namespace, discipline_name, status, comment):
    """
        create and save a study case validation
        :param: study_case_id, id of the studycase
        :type: integer
        :param: user, user that did the validation
        :type: user
        :param: validation_type, type of valisation (data or graph)
        :type: string
        :param: namespace, namespace of the data validated
        :type: string
        :param: discipline_name, discipline of the data validated
        :type: string
        :param: status, state of the validation (validated or not)
        :type: string
        :param: comment, comment
        :type: string
    """
    new_study_validation = StudyCaseValidation()
    new_study_validation.study_case_id = study_case_id
    new_study_validation.validation_user = f'{user.firstname} {user.lastname}'
    new_study_validation.validation_user_department = user.department
    new_study_validation.namespace = namespace
    new_study_validation.discipline_name = discipline_name
    new_study_validation.validation_state = status
    new_study_validation.validation_comment = comment
    new_study_validation.validation_type = validation_type
    new_study_validation.validation_date = datetime.now().astimezone(timezone.utc).replace(tzinfo=None)

    db.session.add(new_study_validation)
    db.session.commit()

    return new_study_validation
