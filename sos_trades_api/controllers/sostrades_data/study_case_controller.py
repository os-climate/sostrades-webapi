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
Study case Functions
"""
from tempfile import gettempdir
import io
from sos_trades_api.tools.code_tools import isevaluatable
from sos_trades_api.tools.right_management.functional.study_case_access_right import (
    StudyCaseAccess,
)
from sos_trades_api.base_server import app, db
from sos_trades_api.tools.coedition.coedition import UserCoeditionAction
from sos_trades_api.models.study_notification import StudyNotification
from sos_trades_api.models.database_models import (
    Notification,
    StudyCaseChange,
    StudyCaseExecutionLog,
    UserStudyPreference,
    StudyCase,
    UserStudyFavorite,
    StudyCaseExecution,
    StudyCaseLog,
)
from sos_trades_api.models.study_case_dto import StudyCaseDto
from sos_trades_api.controllers.sostrades_main.ontology_controller import (
    load_processes_metadata,
    load_repositories_metadata,
)
from sqlalchemy.sql.expression import and_, desc
import json
from sos_trades_api.controllers.error_classes import InvalidFile, InvalidStudy
from sos_trades_api.tools.loading.study_case_manager import StudyCaseManager
from io import BytesIO


def get_user_shared_study_case(user_id):
    """
    Retrieve all the study cases shared with the user
    """

    result = []
    study_case_access = StudyCaseAccess(user_id)

    all_user_studies = study_case_access.user_study_cases

    if len(all_user_studies) > 0:

        # Sort study using creation date
        all_user_studies = sorted(
            all_user_studies, key=lambda res: res.creation_date, reverse=True
        )

        # Apply Ontology
        processes_metadata = []
        repositories_metadata = []

        # Iterate through study to aggregate needed information's
        for user_study in all_user_studies:

            # Manage gathering of all data needed for the ontology request
            process_key = f'{user_study.repository}.{user_study.process}'
            if process_key not in processes_metadata:
                processes_metadata.append(process_key)

            repository_key = user_study.repository

            if repository_key not in repositories_metadata:
                repositories_metadata.append(repository_key)

        process_metadata = load_processes_metadata(processes_metadata)
        repository_metadata = load_repositories_metadata(repositories_metadata)

        # Get all study identifier
        all_study_identifier = [user_study.id for user_study in all_user_studies]

        # Retrieve all favorite study
        all_favorite_studies = (
            UserStudyFavorite.query.filter(
                UserStudyFavorite.study_case_id.in_(all_study_identifier)
            )
            .filter(UserStudyFavorite.user_id == user_id)
            .all()
        )
        all_favorite_studies_identifier = [
            favorite_study.study_case_id for favorite_study in all_favorite_studies
        ]

        # Get all related study case execution id
        all_study_case_execution_identifiers = [
            user_study.current_execution_id
            for user_study in filter(
                lambda s: s.current_execution_id is not None, all_user_studies
            )
        ]
        all_study_case_execution = StudyCaseExecution.query.filter(
            StudyCaseExecution.id.in_(all_study_case_execution_identifiers)
        ).all()

        # Final loop to update study dto
        for user_study in all_user_studies:

            # Update ontology display name
            user_study.apply_ontology(process_metadata, repository_metadata)

            # Manage favorite study list
            if user_study.id in all_favorite_studies_identifier:
                user_study.is_favorite = True

            # Manage execution status
            study_case_execution = list(
                filter(
                    lambda sce: sce.study_case_id == user_study.id,
                    all_study_case_execution,
                )
            )
            if study_case_execution is None or len(study_case_execution) == 0:
                user_study.execution_status = StudyCaseExecution.NOT_EXECUTED
            else:
                user_study.execution_status = study_case_execution[0].execution_status

        result = sorted(all_user_studies, key=lambda res: res.is_favorite, reverse=True)

    return result


def get_change_file_stream(notification_id, parameter_key):
    """
    Get the File from a change notification parameter
    """
    change = (
        StudyCaseChange.query.filter(StudyCaseChange.notification_id == notification_id)
        .filter(StudyCaseChange.variable_id == parameter_key)
        .first()
    )

    if change is not None:
        if change.old_value_blob is not None:
            return BytesIO(change.old_value_blob)

    raise InvalidFile(f'Error, cannot retrieve change file {parameter_key}.csv')


def get_study_case_notifications(study_id, with_notifications):
    """ "
    get list of study case notifications
    :param: study_id, id of the study
    :type: integer
    :param: with_notifications, True to return the modifications, False return an empty list
    :type: boolean

    """
    notification_list = []

    with app.app_context():
        if with_notifications:
            notification_query = (
                Notification.query.filter(Notification.study_case_id == study_id)
                .order_by(Notification.created.desc())
                .all()
            )

            if len(notification_query) > 0:
                for notif in notification_query:
                    new_notif = StudyNotification(
                        notif.id,
                        notif.created,
                        notif.author,
                        notif.type,
                        notif.message,
                        [],
                    )
                    if notif.type == UserCoeditionAction.SAVE:
                        changes_query = (
                            StudyCaseChange.query.filter(
                                StudyCaseChange.notification_id == notif.id
                            )
                            .order_by(StudyCaseChange.last_modified.desc())
                            .all()
                        )

                        if len(changes_query) > 0:
                            notif_changes = []
                            for ch in changes_query:
                                new_change = StudyCaseChange()
                                new_change.id = ch.id
                                new_change.notification_id = notif.id
                                new_change.variable_id = ch.variable_id
                                new_change.variable_type = ch.variable_type
                                new_change.change_type = ch.change_type
                                new_change.new_value = isevaluatable(ch.new_value)
                                new_change.old_value = isevaluatable(ch.old_value)
                                new_change.old_value_blob = ch.old_value_blob
                                new_change.last_modified = ch.last_modified
                                notif_changes.append(new_change)

                            new_notif.changes = notif_changes

                    notification_list.append(new_notif)

        return notification_list


def get_user_authorised_studies_for_process(user_id, process_name, repository_name):
    """
    Retrieve all the study cases shared with the user for the selected process and repository
    """

    result = []
    study_case_access = StudyCaseAccess(user_id)
    all_user_studies = study_case_access.get_study_cases_authorised_from_process(
        process_name, repository_name
    )

    if len(all_user_studies) > 0:
        # Apply Ontology
        processes_metadata = []
        repositories_metadata = []

        process_key = f'{repository_name}.{process_name}'

        if process_key not in processes_metadata:
            processes_metadata.append(process_key)

        repository_key = repository_name

        if repository_key not in repositories_metadata:
            repositories_metadata.append(repository_key)

        process_metadata = load_processes_metadata(processes_metadata)
        repository_metadata = load_repositories_metadata(repositories_metadata)

        for sc in all_user_studies:
            new_study = StudyCaseDto(sc)
            new_study.apply_ontology(process_metadata, repository_metadata)
            result.append(new_study)

    return result


def study_case_logs(study_case_id):
    """
    Retrieve study case logs from database for a given study case

    :param study_case_id: study case identifier
    :type study_case_id: int

    :return: StudyCaseLog[]
    """
    if study_case_id is not None:
        result = []
        try:

            results = StudyCaseLog.query\
                .filter(StudyCase.id.like(study_case_id)
                .order_by(StudyCaseLog.id.desc())
                .limit(200)
                .all())


        except Exception as ex:
            print(ex)
        finally:
            return result

    else:
        raise InvalidStudy(
            f'Requested study case (identifier {study_case_id} does not exist in the database')


def get_logs(study_id=None):
    """ "
    Retrieve a study case execution logs, write them in a file, return the filename
    """
    logs = []
    if study_id is not None:
        logs = (
            StudyCaseExecutionLog.query.filter(
                StudyCaseExecutionLog.study_case_id == study_id
            )
            .order_by(StudyCaseExecutionLog.id.desc())
            .all()
        )
        logs.reverse()

    if logs:
        tmp_folder = gettempdir()
        file_name = f'{tmp_folder}/_log'
        with io.open(file_name, "w", encoding="utf-8") as f:
            for log in logs:
                f.write(
                    f'{log.created}\t{log.name}\t{log.log_level_name}\t{log.message}\n'
                )
        return file_name


def get_raw_logs(study_id):
    """
    Return the location of the raw logs filepath

    :param study_id: study identifier
    :return: raw log filepath or empty string
    """

    study = StudyCaseManager(study_id)

    file_path = ''

    if study is not None:
        file_path = study.raw_log_file_path_absolute()

    return file_path


def load_study_case_preference(study_id, user_id):
    """Load study preferences for the given user

    :params: study_id, study identifier corresponding to the requested preference
    :type: integer
    :params: user_id, user identifier corresponding to the requested preference
    :type: integer

    :return: preference dictionary
    """

    result = {}

    with app.app_context():
        preferences = UserStudyPreference.query.filter(
            and_(
                UserStudyPreference.user_id == user_id,
                UserStudyPreference.study_case_id == study_id,
            )
        ).all()

        if len(preferences) > 0:
            preference = preferences[0].preference

            if len(preference) > 0:
                result = json.loads(preference)

    return result


def save_study_case_preference(study_id, user_id, preference):
    """Load study preferences for the given user

    :params: study_id, study identifier corresponding to the requested preference
    :type: integer
    :params: user_id, user identifier corresponding to the requested preference
    :type: integer
    :params: preference, user study preference
    :type: integer
    """

    result = {}

    with app.app_context():
        preferences = UserStudyPreference.query.filter(
            and_(
                UserStudyPreference.user_id == user_id,
                UserStudyPreference.study_case_id == study_id,
            )
        ).all()

        current_preference = None
        if len(preferences) > 0:
            current_preference = preferences[0]
            current_preference.preference = json.dumps(preference)
        else:
            current_preference = UserStudyPreference()
            current_preference.user_id = user_id
            current_preference.study_case_id = study_id
            current_preference.preference = json.dumps(preference)

        db.session.add(current_preference)
        db.session.commit()

    return result


def set_user_authorized_execution(study_case_id, user_id):
    """
    Save the user authorized for execution of a studycase
    :param: study_case_id, id of the study case
    :type: integer
    :param: user_id, id of the user
    :type: integer
    """
    # Retrieve study case with user authorised for execution
    study_case_loaded = StudyCase.query.filter(StudyCase.id == study_case_id).first()

    if study_case_loaded is not None:
        # Update Study case user id authorised
        study_case_loaded.user_id_execution_authorised = user_id
        db.session.add(study_case_loaded)
        db.session.commit()
    else:
        raise InvalidStudy(
            f'Unable to find in database the study case with id {study_case_id}'
        )

    return 'You successfully claimed Execution ability'


def add_favorite_study_case(study_case_id, user_id):
    """
    create and save a new favorite study case for a user
      :param: study_case_id, id of the study_case
      :type: integer
      :param: user_id, user that did add a favorite study
      :type: integer

    """

    favorite_study = (
        UserStudyFavorite.query.filter(UserStudyFavorite.user_id == user_id)
        .filter(UserStudyFavorite.study_case_id == study_case_id)
        .first()
    )

    # Creation of a favorite study
    if favorite_study is None:
        new_favorite_study = UserStudyFavorite()
        new_favorite_study.study_case_id = study_case_id
        new_favorite_study.user_id = user_id

        db.session.add(new_favorite_study)
        db.session.commit()

        return new_favorite_study

    else:
        study_case = (
            StudyCase.query.filter(StudyCase.id == study_case_id)
            .filter(UserStudyFavorite.study_case_id == study_case_id)
            .first()
        )
        raise Exception(
            f'The study - {study_case.name} - is already in your favorite studies'
        )


def remove_favorite_study_case(study_case_id, user_id):
    """
    remove a favorite study case for a user
      :param: study_case_id, id of the study_case
      :type: integer
      :param: user_id, user that did add a favorite study
      :type: integer

    """
    # Get the study-case thanks to study_id into UserFavoriteStudy
    study_case = (
        StudyCase.query.filter(StudyCase.id == study_case_id)
        .filter(UserStudyFavorite.study_case_id == study_case_id)
        .first()
    )

    favorite_study = (
        UserStudyFavorite.query.filter(UserStudyFavorite.user_id == user_id)
        .filter(UserStudyFavorite.study_case_id == study_case_id)
        .first()
    )

    if favorite_study is not None:
        try:
            db.session.delete(favorite_study)
            db.session.commit()

        except Exception as ex:
            db.session.rollback()
            raise ex
    else:
        raise Exception(f'You cannot remove a study that is not in your favorite study')

    return f'The study, {study_case.name}, has been removed from favorite study.'
