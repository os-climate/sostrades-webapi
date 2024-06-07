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
Data and graph validation tools
"""
from datetime import datetime, timezone

from sos_trades_api.models.database_models import StudyCaseValidation
from sos_trades_api.server.base_server import app, db


def invalidate_namespace_after_save(study_case_id, user_fullname, user_department, namespace):
    """
       If a variable has been changed, retrieve the node validation status, if the node was validated
       that invalidate it. The user have to check changes.

        :param: study_case_id, id of the studycase
        :type: integer
        :param: user_fullname, user's information that did the validation
        :type: user
        :param: user_department, user's information that did the validation
        :type: user
        :param: namespace, namespace of the data validated
        :type: string

    """
    with app.app_context():
        sc_val_query = StudyCaseValidation.query.\
            filter(StudyCaseValidation.study_case_id == study_case_id).\
            filter(StudyCaseValidation.namespace == namespace).\
            order_by(StudyCaseValidation.id.desc()).first()

        # Existing validation found, if validated creating invalidating entry
        if sc_val_query is not None and sc_val_query.validation_state == StudyCaseValidation.VALIDATED:
            new_study_validation = StudyCaseValidation()
            new_study_validation.study_case_id = study_case_id
            new_study_validation.validation_user = user_fullname
            new_study_validation.validation_user_department = user_department
            new_study_validation.namespace = namespace
            new_study_validation.validation_state = StudyCaseValidation.NOT_VALIDATED
            new_study_validation.validation_comment = 'Automatic invalidation after data change(s)'
            new_study_validation.validation_date = datetime.now().astimezone(timezone.utc).replace(tzinfo=None)

            db.session.add(new_study_validation)
            db.session.commit()


def clean_obsolete_data_validation_entries(study_case_manager):
    """
    Retrieve a study case all data validation information and delete obsolete ones (case configure removing nodes
    for example). Remove in database all validation if a parameter does not exist anymore.
    For example in case of a multi-scenario,
    if a node is validated with a scenario 1,2,3,4 and if we change a parameter of scenario 3, a new scenario "4"
    is created with others parameter and we have to delete the validation of the previous scenario "4".
    """
    with app.app_context():
        all_validations_query = StudyCaseValidation.query.filter(StudyCaseValidation.study_case_id ==
                                                                 study_case_manager.study.id).\
            order_by(StudyCaseValidation.id.desc()).all()

        disciplines_dict = study_case_manager.execution_engine.dm.disciplines_dict

        for key in disciplines_dict:
            # Removing from all validations query, validation entries still valid
            all_validations_query = list(filter(lambda val: val.namespace != disciplines_dict[key]["ns_reference"].value,
                                                all_validations_query))

        # After previous loop all_validations_query only contains obsolete validations entries, removing them
        if len(all_validations_query) > 0:
            for val_to_del in all_validations_query:
                db.session.delete(val_to_del)
            db.session.commit()
