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
import shutil
from shutil import rmtree
from datetime import datetime, timezone, timedelta

from sos_trades_api.tools.allocation_management.allocation_management import create_allocation, get_allocation_status, \
    load_study_allocation, delete_study_server_services_and_deployments

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
from sos_trades_api.server.base_server import app, db
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
    StudyCaseAccessGroup,
    StudyCaseAccessUser,
    Group,
    GroupAccessUser,
    AccessRights,
    StudyCaseAllocation
)
from sos_trades_api.models.study_case_dto import StudyCaseDto
from sos_trades_api.controllers.sostrades_data.ontology_controller import (
    load_processes_metadata,
    load_repositories_metadata,
)
from sqlalchemy.sql.expression import and_, desc
import json
from sos_trades_api.controllers.error_classes import InvalidFile, InvalidStudy, InvalidStudyExecution
from sos_trades_api.tools.loading.study_case_manager import StudyCaseManager
from io import BytesIO


def create_empty_study_case(
    user_identifier: int,
    name: str,
    repository_name: str,
    process_name: str,
    group_identifier: int,
):
    """
    Create study case object in database

    :param user_identifier: user identifier that initiate the creation request
    :type user_identifier: int
    :param name: study case name attribute
    :type name: str
    :param repository_name: repository name where the associated process is stored
    :type repository_name: str
    :param process_name: process name that will be used to initialize the study case int the execution engine
    :type process_name: str
    :param group_identifier: group identifier to which the study case will be attached
    :type group_identifier: int
    :return: sos_trades_api.models.database_models.StudyCase
    """

    study_name_list = (
        StudyCase.query.join(StudyCaseAccessGroup)
        .join(Group)
        .join(GroupAccessUser)
        .filter(GroupAccessUser.user_id == user_identifier)
        .filter(Group.id == group_identifier)
        .filter(StudyCase.disabled == False)
        .all()
    )

    for snl in study_name_list:
        if snl.name == name:
            raise InvalidStudy(
                f'The following study case name "{name}" already exist in the database for the selected group'
            )

    # Initialize the new study case object in database
    study_case = StudyCase()
    study_case.group_id = group_identifier
    study_case.repository = repository_name
    study_case.name = name
    study_case.process = process_name

    # Save study_case
    db.session.add(study_case)
    db.session.commit()

    # Add user as owner of the study case
    owner_right = AccessRights.query.filter(
        AccessRights.access_right == AccessRights.OWNER
    ).first()
    if owner_right is not None:
        new_user_access = StudyCaseAccessUser()
        new_user_access.right_id = owner_right.id
        new_user_access.study_case_id = study_case.id
        new_user_access.user_id = user_identifier
        db.session.add(new_user_access)
        db.session.commit()

        # Add study to corresponding group as owner
        new_group_access = StudyCaseAccessGroup()
        new_group_access.group_id = group_identifier
        new_group_access.study_case_id = study_case.id
        new_group_access.right_id = owner_right.id
        db.session.add(new_group_access)
        db.session.commit()

    return study_case


def create_study_case_allocation(study_case_identifier):
    """
    Create a study case allocation instance in order to follow study case resource activation

    :param study_case_identifier: study case identifier to allocate
    :type study_case_identifier: int
    :return: sos_trades_api.models.database_models.StudyCaseAllocation
    """

    # First check that allocated resources does not already exist
    study_case_allocations = StudyCaseAllocation.query.filter(StudyCaseAllocation.study_case_id == study_case_identifier).all()

    if len(study_case_allocations) == 0:
        new_study_case_allocation = create_allocation(study_case_identifier)

    else:
        raise InvalidStudy('Allocation already exist for this study case')

    return new_study_case_allocation


def load_study_case_allocation(study_case_identifier):
    """
    Load a study case allocation and if server mode is kubernetes, check pod status

    ::param study_case_identifier: study case identifier to the allocation to load
    :type study_case_identifier: int
    :return: sos_trades_api.models.database_models.StudyCaseAllocation
    """
    need_reload = False
    study_case_allocations = StudyCaseAllocation.query.filter(StudyCaseAllocation.study_case_id == study_case_identifier).all()
    study_case_allocation = None
    if len(study_case_allocations) > 0:
        study_case_allocation = study_case_allocations[0]
        # First get allocation status
        if study_case_allocation.kubernetes_pod_name is None:
            need_reload = True
        else:
            try:
                study_case_allocation.status = get_allocation_status(study_case_allocation.kubernetes_pod_name)
                need_reload = study_case_allocation.status == StudyCaseAllocation.ERROR
            except:
                study_case_allocation.status = StudyCaseAllocation.ERROR
                need_reload = True
        #if the pod is not launch or accessible, reload pod
        if need_reload:
            study_case_allocation.status = StudyCaseAllocation.IN_PROGRESS
            load_study_allocation(study_case_allocation)

    else:
        study_case_allocation = create_allocation(study_case_identifier)


    return study_case_allocation

def get_study_case_allocation(study_case_identifier):
    """
    Load a study case allocation and if server mode is kubernetes, check pod status

    ::param study_case_identifier: study case identifier to the allocation to load
    :type study_case_identifier: int
    :return: sos_trades_api.models.database_models.StudyCaseAllocation
    """
    study_case_allocations = StudyCaseAllocation.query.filter(StudyCaseAllocation.study_case_id == study_case_identifier).all()
    study_case_allocation = None
    if len(study_case_allocations) > 0:
        study_case_allocation = study_case_allocations[0]
        try:
            study_case_allocation.status = get_allocation_status(study_case_allocation.kubernetes_pod_name)
        except Exception as exc:
            study_case_allocation.status = StudyCaseAllocation.ERROR
            study_case_allocation.message = str(exc)
    return study_case_allocation


def edit_study(study_id, new_group_id, new_study_name, user_id):
    """
    Update the group and the study_name for a study case
    :param study_id: id of the study to load
    :type study_id: integer
    :param new_group_id: id of the new group of the study
    :type new_group_id:  integer
    :param new_study_name: new name of the study
    :type new_study_name: string
    :param user_id: id of the current user.
    :type user_id: integer

    """
    study_is_updated = False

    # Check if the study is not in calculation execution
    study_case_execution = StudyCaseExecution.query.filter(StudyCaseExecution.study_case_id == study_id)\
        .order_by(desc(StudyCaseExecution.id)).first()

    if study_case_execution is None or (study_case_execution.execution_status != StudyCaseExecution.RUNNING and
                                        study_case_execution.execution_status != StudyCaseExecution.PENDING):

        # Retrieve study, StudyCaseManager throw an exception if study does not exist
        study_case_manager = StudyCaseManager(study_id)

        update_study_name = study_case_manager.study.name != new_study_name
        update_group_id = study_case_manager.study.group_id != new_group_id
        # ---------------------------------------------------------------
        # First make update operation on data's (database and filesystem)

        # Perform database update
        if update_study_name or update_group_id:
            study_to_update = StudyCase.query.filter(StudyCase.id == study_id).first()
            if study_to_update is not None:
                # Verify if the name already exist in the target group
                study_name_list = StudyCase.query.join(StudyCaseAccessGroup).join(
                    Group).join(GroupAccessUser) \
                    .filter(GroupAccessUser.user_id == user_id) \
                    .filter(Group.id == new_group_id) \
                    .filter(StudyCase.disabled == False).all()

                for study in study_name_list:
                    if study.name == new_study_name:
                        raise InvalidStudy(
                            f'The following study case name "{new_study_name}" already exist in the database for the target group')

                # Retrieve the study group access
                update_group_access = StudyCaseAccessGroup.query \
                    .filter(StudyCaseAccessGroup.study_case_id == study_id) \
                    .filter(StudyCaseAccessGroup.group_id == study_to_update.group_id).first()
                try:
                    if update_study_name:
                        study_to_update.name = new_study_name

                    if update_group_id:

                        study_to_update.group_id = new_group_id

                        if update_group_access is not None:

                            update_group_access.group_id = new_group_id
                            db.session.add(update_group_access)
                            db.session.commit()

                    # Update study last modification
                    new_modification_date = datetime.now().astimezone(timezone.utc).replace(tzinfo=None)
                    if study_to_update.modification_date >= new_modification_date:
                        study_to_update.modification_date = study_to_update.modification_date + timedelta(seconds=5)
                    else:
                        study_to_update.modification_date = new_modification_date

                    db.session.add(study_to_update)
                    db.session.commit()

                except Exception as ex:
                    db.session.rollback()
                    raise ex

                # -----------------------------------------------------------------
                # manage the read only mode file:

                # we don't want the study to be reload in read only before the update is done
                # so we remove the read_only_file if it exists, it will be updated at the end of the reload
                try:
                    study_case_manager.delete_loaded_study_case_in_json_file()
                except BaseException as ex:
                    app.logger.error(
                        f'Study {study_id} updated with name {new_study_name} and group {new_group_id} error for deleting readonly file')

                # If group has change then move file (can only be done after the study 'add')
                if update_group_id:
                    updated_study_case_manager = StudyCaseManager(study_id)
                    try:
                        shutil.move(study_case_manager.dump_directory, updated_study_case_manager.dump_directory)
                    except BaseException as ex:
                        db.session.rollback()
                        raise ex

                study_is_updated = study_to_update.name == new_study_name
                app.logger.info(
                    f'Study {study_id} has been successfully updated with name {new_study_name} and group {new_group_id}')

                return study_is_updated
            else:
                raise InvalidStudy(f'Requested study case (identifier {study_id} does not exist in the database')
    else:
        raise InvalidStudyExecution("This study is running, you cannot edit it during its run.")


def delete_study_cases_and_allocation(studies):
    """
    Delete one or multiple study cases from database and disk
    :param: studies, list of studycase ids to be deleted
    :type: list of integers
    """
    # Verify that we find same number of studies by querying database
    with app.app_context():
        query = StudyCase.query.filter(StudyCase.id.in_(
            studies)).all()
        query_allocations = StudyCaseAllocation.query.filter(StudyCaseAllocation.study_case_id.in_(
            studies)).all()
        pod_names = [allocation.kubernetes_pod_name for allocation in query_allocations]
        if len(query) == len(studies):
            try:
                for sc in query:
                    db.session.delete(sc)
                db.session.commit()
            except Exception as ex:
                db.session.rollback()
                raise ex

            # Once removed from db, remove it from file system
            for study in query:
                folder = StudyCaseManager.get_root_study_data_folder(study.group_id, study.id)
                rmtree(folder, ignore_errors=True)

            delete_study_server_services_and_deployments(pod_names)


            return f'All the studies (identifier(s) {studies}) have been deleted in the database'
        else:
            raise InvalidStudy(f'Unable to find all the study cases to delete in the database, '
                               f'please refresh your study cases list')


def get_user_shared_study_case(user_identifier: int):
    """
    Retrieve all the study cases shared with the user

    :param user_identifier: user identifier for which available study will be extracted
    :type user_identifier: int
    :return: sos_trades_api.models.database_models.StudyCase
    """

    result = []
    study_case_access = StudyCaseAccess(user_identifier)

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
            .filter(UserStudyFavorite.user_id == user_identifier)
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


def get_change_file_stream(notification_identifier, parameter_key):
    """
    Get the File from a change notification parameter

    :param notification_identifier: notification identifier to look
    :type notification_identifier: int
    :param parameter_key: parameter for which changes will be extracted
    :type parameter_key: str
    :return: BytesIO
    """

    change = (
        StudyCaseChange.query.filter(
            StudyCaseChange.notification_id == notification_identifier
        )
        .filter(StudyCaseChange.variable_id == parameter_key)
        .first()
    )

    if change is not None:
        if change.old_value_blob is not None:
            return BytesIO(change.old_value_blob)

    raise InvalidFile(f'Error, cannot retrieve change file {parameter_key}.csv')


def get_study_case_notifications(study_identifier):
    """
    Get study case notification list

    :param study_identifier: study identifier to look
    :type study_identifier: int
    :return: sos_trades_api.models.database_models.Notification[]
    """
    notification_list = []

    with app.app_context():

        notification_query = (
            Notification.query.filter(Notification.study_case_id == study_identifier)
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


def get_user_authorised_studies_for_process(
    user_identifier, process_name, repository_name
):
    """
    Retrieve all the study cases shared with the user for the selected process and repository

    :param user_identifier: user identifier use to filter available study case
    :type user_identifier: int
    :param process_name: process name use to filter study case
    :type process_name: str
    :param repository_name: repository name that host process
    :type repository_name: str
    :return: sos_trades_api.models.study_case_dto.StudyCaseDto
    """

    result = []
    study_case_access = StudyCaseAccess(user_identifier)
    all_user_studies = study_case_access.get_study_cases_authorised_from_process(
        process_name, repository_name
    )

    if len(all_user_studies) > 0:
        # Apply Ontology
        processes_metadata = [f'{repository_name}.{process_name}']
        repositories_metadata = [repository_name]

        process_metadata = load_processes_metadata(processes_metadata)
        repository_metadata = load_repositories_metadata(repositories_metadata)

        for sc in all_user_studies:
            new_study = StudyCaseDto(sc)
            new_study.apply_ontology(process_metadata, repository_metadata)
            result.append(new_study)

    return result


def study_case_logs(study_case_identifier):
    """
    Retrieve study case logs from database for a given study case

    :param study_case_identifier: study case identifier for which logs will be retrieved
    :type study_case_identifier: int
    :return: sos_trades_api.models.database_models.StudyCaseLog[]
    """

    if study_case_identifier is not None:
        result = []
        try:
            result = (
                StudyCaseLog.query.filter(
                    StudyCaseLog.study_case_id == study_case_identifier
                )
                .order_by(StudyCaseLog.id)
                .limit(200)
                .all()
            )
        except Exception as ex:
            print(ex)
        finally:
            return result
    else:
        raise InvalidStudy(
            f'Requested study case (identifier {study_case_identifier} does not exist in the database'
        )


def get_logs(study_case_identifier):
    """
    Retrieve a study case execution logs, write them in a file, return the filename

    :param study_case_identifier: study case identifier for which we will retrieve execution log
    :type study_case_identifier: int
    :return: str (filename)
    """
    logs = []
    if study_case_identifier is not None:
        logs = (
            StudyCaseExecutionLog.query.filter(
                StudyCaseExecutionLog.study_case_id == study_case_identifier
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


def get_raw_logs(study_case_identifier):
    """
    Return the location of the raw logs file path

    :param study_case_identifier: study identifier to the log file to retrieve
    :type study_case_identifier: int
    :return: raw log file path or empty string
    """

    study = StudyCaseManager(study_case_identifier)

    file_path = ''

    if study is not None:
        file_path = study.raw_log_file_path_absolute()

    return file_path


def load_study_case_preference(study_case_identifier, user_identifier):
    """
    Load study preferences for the given user

    :param study_case_identifier: study case identifier corresponding to the requested preference
    :type study_case_identifier: int
    :param user_identifier: user identifier corresponding to the requested preference
    :type user_identifier: int

    :return: preference dictionary
    """

    result = {}

    with app.app_context():
        preferences = UserStudyPreference.query.filter(
            and_(
                UserStudyPreference.user_id == user_identifier,
                UserStudyPreference.study_case_id == study_case_identifier,
            )
        ).all()

        if len(preferences) > 0:
            preference = preferences[0].preference

            if len(preference) > 0:
                result = json.loads(preference)

    return result


def save_study_case_preference(study_case_identifier, user_identifier, preference):
    """
    Load study preferences for the given user

    :param study_case_identifier: study identifier corresponding to the requested preference
    :type study_case_identifier: int
    :param user_identifier: user identifier corresponding to the requested preference
    :type user_identifier: int
    :param preference: user study preference
    :type preference: int
    """

    result = {}

    with app.app_context():
        preferences = UserStudyPreference.query.filter(
            and_(
                UserStudyPreference.user_id == user_identifier,
                UserStudyPreference.study_case_id == study_case_identifier,
            )
        ).all()

        current_preference = None
        if len(preferences) > 0:
            current_preference = preferences[0]
            current_preference.preference = json.dumps(preference)
        else:
            current_preference = UserStudyPreference()
            current_preference.user_id = user_identifier
            current_preference.study_case_id = study_case_identifier
            current_preference.preference = json.dumps(preference)

        db.session.add(current_preference)
        db.session.commit()

    return result


def set_user_authorized_execution(study_case_identifier, user_identifier):
    """
    Save the user authorized for execution of a study case

    :param study_case_identifier: identifier of the study case
    :type study_case_identifier: int
    :param user_identifier: id of the user
    :type user_identifier: int
    """
    # Retrieve study case with user authorised for execution
    study_case_loaded = StudyCase.query.filter(
        StudyCase.id == study_case_identifier
    ).first()

    if study_case_loaded is not None:
        # Update Study case user id authorised
        study_case_loaded.user_id_execution_authorised = user_identifier
        db.session.add(study_case_loaded)
        db.session.commit()
    else:
        raise InvalidStudy(
            f'Unable to find in database the study case with id {study_case_identifier}'
        )

    return 'You successfully claimed Execution ability'


def add_favorite_study_case(study_case_identifier, user_identifier):
    """
    Create and save a new favorite study case for a user

    :param study_case_identifier: id of the study_case
    :type study_case_identifier: int
    :param user_identifier: user that did add a favorite study
    :type user_identifier: int

    """

    favorite_study = (
        UserStudyFavorite.query.filter(UserStudyFavorite.user_id == user_identifier)
        .filter(UserStudyFavorite.study_case_id == study_case_identifier)
        .first()
    )

    # Creation of a favorite study
    if favorite_study is None:
        new_favorite_study = UserStudyFavorite()
        new_favorite_study.study_case_id = study_case_identifier
        new_favorite_study.user_id = user_identifier

        db.session.add(new_favorite_study)
        db.session.commit()

        return new_favorite_study

    else:
        study_case = (
            StudyCase.query.filter(StudyCase.id == study_case_identifier)
            .filter(UserStudyFavorite.study_case_id == study_case_identifier)
            .first()
        )
        raise Exception(
            f'The study - {study_case.name} - is already in your favorite studies'
        )


def remove_favorite_study_case(study_case_identifier, user_identifier):
    """
    Remove a favorite study case for a user

    :param study_case_identifier: identifier of the study_case
    :type study_case_identifier: int
    :param user_identifier: user that did add a favorite study
    :type user_identifier: int
    """

    # Get the study-case thanks to study_id into UserFavoriteStudy
    study_case = (
        StudyCase.query.filter(StudyCase.id == study_case_identifier)
        .filter(UserStudyFavorite.study_case_id == study_case_identifier)
        .first()
    )

    favorite_study = (
        UserStudyFavorite.query.filter(UserStudyFavorite.user_id == user_identifier)
        .filter(UserStudyFavorite.study_case_id == study_case_identifier)
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
