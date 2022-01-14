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
from sos_trades_api.base_server import db, app
from datetime import datetime, timezone
from sos_trades_api.models.database_models import StudyCaseValidation


def invalidate_discipline_after_save(study_case_id, user_fullname, user_department, namespace, discipline_name):
    """
        Retrieve a discipline data validation status, if discipline was data validated invalidate it
    """
    with app.app_context():
        sc_val_query = StudyCaseValidation.query.\
            filter(StudyCaseValidation.study_case_id == study_case_id).\
            filter(StudyCaseValidation.validation_type == StudyCaseValidation.VALIDATION_DATA).\
            filter(StudyCaseValidation.namespace == namespace).\
            filter(StudyCaseValidation.discipline_name == discipline_name).\
            order_by(StudyCaseValidation.id.desc()).first()

        # Existing validation found, if validated creating invalidating entry
        if sc_val_query is not None and sc_val_query.validation_state == StudyCaseValidation.VALIDATED:
            new_study_validation = StudyCaseValidation()
            new_study_validation.study_case_id = study_case_id
            new_study_validation.validation_user = user_fullname
            new_study_validation.validation_user_department = user_department
            new_study_validation.namespace = namespace
            new_study_validation.discipline_name = discipline_name
            new_study_validation.validation_state = StudyCaseValidation.NOT_VALIDATED
            new_study_validation.validation_comment = 'Automatic invalidation after data change(s)'
            new_study_validation.validation_type = StudyCaseValidation.VALIDATION_DATA
            new_study_validation.validation_date = datetime.now().astimezone(timezone.utc).replace(tzinfo=None)

            db.session.add(new_study_validation)
            db.session.commit()

        # Even if no validation, safely remove graph validation for the entire study
        clean_graph_validation_from_study_case(study_case_id)


def clean_graph_validation_from_study_case(study_case_id):
    """
    Retrieve a study case all graph validation information and delete them
    """
    with app.app_context():
        sc_graph_val_del_query = StudyCaseValidation.query.filter(StudyCaseValidation.study_case_id == study_case_id).\
            filter(StudyCaseValidation.validation_type == StudyCaseValidation.VALIDATION_GRAPH).all()

        if len(sc_graph_val_del_query) > 0:
            for val_item in sc_graph_val_del_query:
                db.session.delete(val_item)
            db.session.commit()


def clean_obsolete_data_validation_entries(study_case_manager):
    """
    Retrieve a study case all data validation information and delete obsolete ones (case configure removing nodes
    for example)
    """
    with app.app_context():
        all_validations_query = StudyCaseValidation.query.filter(StudyCaseValidation.study_case_id ==
                                                                 study_case_manager.study.id).\
            order_by(StudyCaseValidation.id.desc()).all()

        disciplines_dict = study_case_manager.execution_engine.dm.disciplines_dict

        for key in disciplines_dict:
            # Removing from all validations query, validation entries still valid
            all_validations_query = list(filter(lambda val: f'{val.namespace}.{val.discipline_name}' !=
                                                            f'{disciplines_dict[key]["ns_reference"].value}.'
                                                            f'{disciplines_dict[key]["model_name_full_path"]}'
                                                            and
                                                            f'{val.namespace}.{val.discipline_name}' !=
                                                            f'{disciplines_dict[key]["ns_reference"].value}.Data',
                                                all_validations_query))

        # After previous loop all_validations_query only contains obsolete validations entries, removing them
        if len(all_validations_query) > 0:
            for val_to_del in all_validations_query:
                db.session.delete(val_to_del)
            db.session.commit()
