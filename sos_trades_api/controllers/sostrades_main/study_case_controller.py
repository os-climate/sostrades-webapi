'''
Copyright 2022 Airbus SAS
Modifications on 2023/08/30-2024/06/24 Copyright 2023 Capgemini

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
import importlib.util
import os
import shutil
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from os import remove
from os.path import join
from shutil import rmtree
from tempfile import gettempdir

import pandas as pd
from numpy import array
from sostrades_core.datasets.dataset_mapping import (
    DatasetsMapping,
    DatasetsMappingException,
)
from sostrades_core.execution_engine.data_manager import DataManager
from sostrades_core.execution_engine.proxy_discipline import ProxyDiscipline
from sostrades_core.tools.proc_builder.process_builder_parameter_type import (
    ProcessBuilderParameterType,
)
from sostrades_core.tools.rw.load_dump_dm_data import DirectLoadDump
from sostrades_core.tools.tree.deserialization import isevaluatable
from sostrades_core.tools.tree.serializer import DataSerializer
from sostrades_core.tools.tree.treenode import TreeNode
from sqlalchemy import desc
from werkzeug.utils import secure_filename

from sos_trades_api.config import Config
from sos_trades_api.controllers.error_classes import (
    InvalidFile,
    InvalidStudy,
    StudyCaseError,
)
from sos_trades_api.controllers.sostrades_data.calculation_controller import (
    calculation_status,
)
from sos_trades_api.controllers.sostrades_data.ontology_controller import (
    load_processes_metadata,
    load_repositories_metadata,
)
from sos_trades_api.controllers.sostrades_data.study_case_controller import (
    add_last_opened_study_case,
)
from sos_trades_api.models.database_models import (
    AccessRights,
    PodAllocation,
    ReferenceStudy,
    StudyCase,
    StudyCaseChange,
    StudyCaseExecution,
    User,
)
from sos_trades_api.models.loaded_study_case import LoadedStudyCase, LoadStatus
from sos_trades_api.models.study_case_dto import StudyCaseDto
from sos_trades_api.server.base_server import app, db, study_case_cache
from sos_trades_api.tools.active_study_management.active_study_management import (
    check_studies_last_active_date,
    delete_study_last_active_file,
    save_study_last_active_date,
)
from sos_trades_api.tools.allocation_management.allocation_management import (
    delete_study_server_services_and_deployments,
)
from sos_trades_api.tools.coedition.coedition import (
    CoeditionMessage,
    UserCoeditionAction,
    add_change_db,
    add_notification_db,
)
from sos_trades_api.tools.data_graph_validation.data_graph_validation import (
    invalidate_namespace_after_save,
)
from sos_trades_api.tools.loading.loading_study_and_engine import (
    study_case_manager_export_from_dataset_mapping,
    study_case_manager_loading,
    study_case_manager_loading_from_reference,
    study_case_manager_loading_from_study,
    study_case_manager_loading_from_usecase_data,
    study_case_manager_update,
    study_case_manager_update_from_dataset_mapping,
)
from sos_trades_api.tools.loading.study_case_manager import StudyCaseManager

"""
Study case Functions
"""

"""
background loading section
"""
def load_or_create_study_case(study_case_identifier):
    """
    Check creation status in database, if not_started: create the studycase, else load it
    Check creation status in database, if creation not_started: create the studycase, else load it
    :param study_case_identifier: study id to load or create
    :type study_case_identifier: integer
    """
    with app.app_context():
        study_case_manager = study_case_cache.get_study_case(study_case_identifier, False)
        # get the studycase in database (created on data server side)

        study_case = StudyCase.query.filter(StudyCase.id.like(study_case_identifier)).first()
        # if the study is not loaded and the creation is not started or finished, create the study
        if study_case.creation_status != StudyCase.CREATION_DONE and study_case.creation_status != ProxyDiscipline.STATUS_DONE:
            study_case_manager.study.creation_status = StudyCase.CREATION_IN_PROGRESS
            study_case.creation_status = StudyCase.CREATION_IN_PROGRESS
            db.session.add(study_case)
            db.session.commit()
            # check if it is a from a copy or an usecase
            if study_case_manager.study.from_type == StudyCase.FROM_STUDYCASE:
                # if it is a copy, get the source study in database
                source_id = int(study_case_manager.study.reference)
                source_study_case = StudyCase.query.filter(StudyCase.id == source_id).first()
                # check that the source study is created, if not raise an error
                if source_study_case is not None and (source_study_case.creation_status != StudyCase.CREATION_DONE and source_study_case.creation_status != ProxyDiscipline.STATUS_DONE):
                    study_case = StudyCase.query.filter(StudyCase.id == study_case_identifier).first()
                    db.session.delete(study_case)
                    db.session.commit()
                    raise Exception("Source study case is not completely created. Load it again then copy it.")
                # copy the study from the source study
                _copy_study_case(study_case_identifier, source_id)
            else:
                # create the study case with all info in database
                _create_study_case(study_case_identifier, study_case_manager.study.reference, study_case_manager.study.from_type)
        else:
            # load the study case as it has already been created
            load_study_case(study_case_identifier)


def load_study_case(study_id, reload=False):
    """
    load study case in background and reload if asked
    :params: study_id, id of the study to load
    :type: integer
    :params: study_access_right, information about the access right needed for the study
    :type: AccessRights enum
    :params: user_id, user id that want to access the study (to get preferences)
    :type: integer
    :params: reload, indicates if the study must be reloaded, false by default
    :type: boolean
    """
    study_manager = study_case_cache.get_study_case(study_id, False)

    if reload:
        study_manager.study_case_manager_reload_backup_files()
        study_manager.reset()

    _launch_load_study_in_background(study_manager, False, False)


def light_load_study_case(study_id, reload=False):
    """
    Launch only the load study in cache
    :params: study_id, id of the study to load
    :type: integer
    :params: study_access_right, information about the access right needed for the study
    :type: AccessRights enum
    """
    study_manager = study_case_cache.get_study_case(study_id, False)
    study_manager.detach_logger()
    if reload:
        study_manager.study_case_manager_reload_backup_files()
        study_manager.reset()

    if study_manager.load_status == LoadStatus.NONE:
        study_case_manager_loading(study_manager, False, False)

    study_manager.attach_logger()
    return study_manager


# END BACKGROUND LOADING FUNCTION section


def get_study_case(user_id, study_case_identifier, study_access_right=None, read_only_mode=False):
    """
    get a loaded studycase in read only if needed or not, launch load_or_create if it is not in cache

    """
    with app.app_context():
        # check if the study needs to be created or needs reload
        load_or_create_study_case(study_case_identifier)

        study_case_manager = study_case_cache.get_study_case(study_case_identifier, False)
        study_case = StudyCase.query.filter(StudyCase.id == study_case_identifier).first()
        study_case_execution = None

        # retrieve study execution status
        is_read_only_possible = False
        if study_case is not None and study_case.current_execution_id is not None:
            study_case_execution = StudyCaseExecution.query.filter(
                StudyCaseExecution.id == study_case.current_execution_id).first()
            # check that the execution is finished to show the read only mode
            if study_case_execution is not None and study_case_execution.execution_status == StudyCaseExecution.FINISHED:
                is_read_only_possible = True

        # check there was no error during loading
        if study_case_manager.load_status == LoadStatus.IN_ERROR:
            raise Exception(study_case_manager.error_message)

        # check access to data with user rights
        read_only = study_access_right == AccessRights.COMMENTER
        no_data = study_access_right == AccessRights.RESTRICTED_VIEWER

        loaded_study_case = None

        # show read_only_mode if needed and possible
        if read_only_mode and is_read_only_possible:
            loaded_study_case = get_loaded_study_case_in_read_only_mode(study_case_identifier, study_access_right)
            # Add this study in last study opened in database
            add_last_opened_study_case(study_case_identifier, user_id)

        # get loaded study in edition mode or if there was a problem with read_only mode
        if loaded_study_case is None:

            loaded_study_case = LoadedStudyCase(study_case_manager, no_data, read_only, user_id)
            # update access rights
            if study_access_right == AccessRights.MANAGER:
                loaded_study_case.study_case.is_manager = True
            elif study_access_right == AccessRights.CONTRIBUTOR:
                loaded_study_case.study_case.is_contributor = True
            elif study_access_right == AccessRights.COMMENTER:
                loaded_study_case.study_case.is_commenter = True
            else:
                loaded_study_case.study_case.is_restricted_viewer = True

            if study_case_manager.load_status == LoadStatus.LOADED:
                # update ontology
                process_metadata = load_processes_metadata(
                    [f"{loaded_study_case.study_case.repository}.{loaded_study_case.study_case.process}"])

                repository_metadata = load_repositories_metadata(
                    [loaded_study_case.study_case.repository])

                loaded_study_case.study_case.apply_ontology(
                    process_metadata, repository_metadata)

                # get execution status
                if study_case_execution is not None:
                    loaded_study_case.study_case.execution_status = study_case_execution.execution_status
                    loaded_study_case.study_case.last_memory_usage = study_case_execution.memory_usage
                    loaded_study_case.study_case.last_cpu_usage = study_case_execution.cpu_usage

                # Read dashboard and set it to the loaded studycase
                # If the root process is at done
                if study_case_manager.execution_engine.root_process.status == ProxyDiscipline.STATUS_DONE:
                    loaded_study_case.dashboard = get_study_dashboard_in_file(study_case_identifier)

                # Add this study in last study opened in database
                add_last_opened_study_case(study_case_identifier, user_id)

    # return study case in read only mode, loaded or with loading status in progress
    return loaded_study_case


def get_loaded_study_case_in_read_only_mode(study_id, study_access_right):
    # Proceeding after rights verification
    # Get readonly file, in case of a restricted viewer get with no_data
    study_json = get_study_in_read_only_mode(
        study_id, study_access_right == AccessRights.RESTRICTED_VIEWER)

    # check in read only file that the study status is DONE
    if study_json is not None and study_json != "null":
        study_case_value = study_json.get("study_case")
        if study_case_value is not None:
            # set study access rights
            if study_access_right == AccessRights.MANAGER:
                study_json["study_case"]["is_manager"] = True
            elif study_access_right == AccessRights.CONTRIBUTOR:
                study_json["study_case"]["is_contributor"] = True
            elif study_access_right == AccessRights.COMMENTER:
                study_json["study_case"]["is_commenter"] = True
            else:
                study_json["study_case"]["is_restricted_viewer"] = True

            return study_json

    return None


def get_study_load_status(study_id):
    """
    Check study case is in cache and return its status
    """
    is_loaded = study_case_cache.is_study_case_cached(study_id)
    status = LoadStatus.NONE
    if is_loaded:
        study_manager = study_case_cache.get_study_case(study_id, False, False)
        status = study_manager.load_status

    return status


def _create_study_case(study_case_identifier, reference, from_type=None):
    """
    Create a study case for the user, adding reference data if specified, then launch loading in background from reference or usecase
    """
    status = StudyCaseExecution.NOT_EXECUTED

    try:

        study_case_manager = study_case_cache.get_study_case(study_case_identifier, False)

        study_case = None
        with app.app_context():
            study_case = StudyCase.query.filter(StudyCase.id == study_case_identifier).first()

            if from_type == StudyCase.FROM_REFERENCE:
                # Get reference path
                reference_path = f"{study_case.repository}.{study_case.process}.{reference}"

                # Generate execution status
                reference_study = ReferenceStudy.query.filter(ReferenceStudy.name == reference) \
                    .filter(ReferenceStudy.reference_path == reference_path).first()
                if reference_study is not None:
                    status = reference_study.execution_status

                    if reference_study.execution_status == ReferenceStudy.UNKNOWN:
                        status = StudyCaseExecution.NOT_EXECUTED

                    new_study_case_execution = StudyCaseExecution()
                    new_study_case_execution.study_case_id = study_case.id
                    new_study_case_execution.execution_status = status
                    new_study_case_execution.creation_date = datetime.now().astimezone(timezone.utc).replace(
                        tzinfo=None)
                    new_study_case_execution.requested_by = "reference"
                    db.session.add(new_study_case_execution)
                    db.session.commit()
                    study_case.current_execution_id = new_study_case_execution.id
                    db.session.add(study_case)
                    db.session.commit()

            # Persist data using the current persistence strategy
            study_case_manager.dump_data(study_case_manager.dump_directory)
            study_case_manager.dump_disciplines_data(
                study_case_manager.dump_directory)

            # Loading data for study created empty
            if reference is None:
                study_case.creation_status = StudyCase.CREATION_DONE
                db.session.add(study_case)
                db.session.commit()
                study_case_manager.load_status = LoadStatus.LOADED
                study_case_manager.n2_diagram = {}
                study_case_manager.execution_engine.dm.treeview = None
                study_case_manager.execution_engine.get_treeview(False, False)

            # Adding reference data and loading study data
            elif from_type == StudyCase.FROM_REFERENCE:

                reference_basepath = Config().reference_root_dir

                db.session.add(study_case)
                # Build reference folder base on study process name and
                # repository
                reference_folder = join(reference_basepath, study_case.repository, study_case.process, reference)

                # Get ref generation ID associated to this ref
                reference_identifier = f"{study_case.repository}.{study_case.process}.{reference}"

                if study_case_manager.load_status != LoadStatus.IN_PROGESS and study_case_manager.load_status != LoadStatus.LOADED:
                    study_case_manager.load_status = LoadStatus.IN_PROGESS

                    # Set creation is done
                    study_case.creation_status = StudyCase.CREATION_DONE
                    db.session.add(study_case)
                    db.session.commit()
                    # Then load data
                    threading.Thread(
                        target=study_case_manager_loading_from_reference,
                        args=(study_case_manager, False, False, reference_folder, reference_identifier)).start()

            elif from_type == "UsecaseData":

                db.session.add(study_case)
                if study_case_manager.load_status == LoadStatus.NONE:
                    study_case_manager.load_status = LoadStatus.IN_PROGESS
                    # Then load data
                    threading.Thread(
                        target=study_case_manager_loading_from_usecase_data,
                        args=(study_case_manager, False, False, study_case.repository, study_case.process, reference)).start()

            # Update cache modification date and release study
            study_case_cache.update_study_case_modification_date(study_case.id, study_case.modification_date)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        study_case_manager.set_error(
            "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)), True)

        # Then propagate exception
        raise Exception(study_case_manager.error_message)


def _copy_study_case(study_id, source_study_case_identifier):
    """
    copy an existing study case with a new name
    :param study_id: study case identifier to modify
    :type study_id:  integer
    :param source_study_case_identifier: identifier of the study case to copy
    :type source_study_case_identifier: int

    """
    with app.app_context():
        study_manager_source = study_case_cache.get_study_case(source_study_case_identifier, False)

        # Copy the last study case execution and then update study_id, creation
        # date and request_by.
        study_execution = StudyCaseExecution.query.filter(StudyCaseExecution.study_case_id == source_study_case_identifier) \
            .order_by(desc(StudyCaseExecution.id)).first()

        status = StudyCaseExecution.NOT_EXECUTED

        study_case = StudyCase.query.filter(StudyCase.id == study_id).first()

        if study_execution is not None:

            if study_execution.execution_status == StudyCaseExecution.RUNNING \
                    or study_execution.execution_status == StudyCaseExecution.STOPPED \
                    or study_execution.execution_status == StudyCaseExecution.PENDING \
                    or study_execution.execution_status == StudyCaseExecution.POD_PENDING:
                status = StudyCaseExecution.NOT_EXECUTED
            else:
                status = study_execution.execution_status

            new_study_execution = StudyCaseExecution()
            new_study_execution.study_case_id = study_case.id
            new_study_execution.execution_status = status
            new_study_execution.execution_type = study_execution.execution_type
            new_study_execution.requested_by = study_execution.requested_by

            db.session.add(new_study_execution)
            db.session.commit()

            study_case.current_execution_id = new_study_execution.id
            db.session.add(study_case)
            db.session.commit()

        try:
            study_manager = study_case_cache.get_study_case(study_case.id, False)

            if study_manager.load_status == LoadStatus.NONE:
                study_manager.load_status = LoadStatus.IN_PROGESS
                threading.Thread(
                    target=study_case_manager_loading_from_study,
                    args=(study_manager, False, False, study_manager_source)).start()

            if study_manager.load_status == LoadStatus.IN_ERROR:
                raise Exception(study_manager.error_message)

            # Update cache modification date and release study
            study_case_cache.update_study_case_modification_date(
                study_case.id, study_case.modification_date)

            # Copy log file from studyExecutionLog
            if study_execution is not None:
                file_path_initial = study_manager_source.raw_log_file_path_absolute()
                # Check if file_path_initial exist
                if os.path.exists(file_path_initial):
                    file_path_final = study_manager.raw_log_file_path_absolute()

                    # Create a folder if the thread 'study_case_manager_loading_from_study'
                    # does not have time to create it
                    path_folder_final = os.path.dirname(file_path_final)
                    if not os.path.exists(path_folder_final):
                        os.mkdir(path_folder_final)
                    try:
                        shutil.copyfile(file_path_initial, file_path_final)
                    except BaseException as ex:
                        raise ex

        except:

            exc_type, exc_value, exc_traceback = sys.exc_info()
            study_manager.set_error(
                "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))

            # Then propagate exception
            raise Exception(study_manager.error_message)

def _launch_load_study_in_background(study_manager,  no_data, read_only):
    """
    Launch only the background thread
    """
    if study_manager.load_status == LoadStatus.NONE:
        study_manager.load_status = LoadStatus.IN_PROGESS
        threading.Thread(
            target=study_case_manager_loading, args=(study_manager, no_data, read_only)).start()

def update_study_parameters_from_datasets_mapping(study_id, user, datasets_mapping, notification_id):
    """
    Configure the study case in the data manager  from a dataset
    :param: study_id, id of the study
    :type: integer
    :param: user, user that did the modification of parameters
    :type: integer
    :param: datasets_mapping, namespace+parameter to connector_id+dataset_id+parameter mapping
    :type: dict
    """
    try:
        # Retrieve study_manager
        study_manager = study_case_cache.get_study_case(study_id, True)

        # Deserialize mapping
        datasets_mapping_deserialized = DatasetsMapping.deserialize(datasets_mapping)

        # Launch load study-case with new parameters from dataset
        if study_manager.load_status != LoadStatus.IN_PROGESS:
            study_manager.clear_error()
            study_manager.load_status = LoadStatus.IN_PROGESS
            threading.Thread(
                target=study_case_manager_update_from_dataset_mapping,
                args=(study_manager, datasets_mapping_deserialized, notification_id),
            ).start()

        if study_manager.load_status == LoadStatus.IN_ERROR:
            raise Exception(study_manager.error_message)


        # Releasing study
        study_case_cache.release_study_case(study_id)

        # Return logical treeview coming from execution engine
        loaded_study_case = LoadedStudyCase(study_manager, False, False, user.id)

        return loaded_study_case
    except DatasetsMappingException as exception :
        # Releasing study
        study_case_cache.release_study_case(study_id)
        app.logger.exception(
            f"Error when updating in background (from datasets mapping) {study_manager.study.name}:{exception}")
        raise exception
    except Exception as error:
        # Releasing study
        study_case_cache.release_study_case(study_id)
        raise StudyCaseError(error)

def export_study_parameters_from_datasets_mapping(study_id, user, datasets_mapping, notification_id):
    """
    Export study parameters in datasets defined in the mapping file
    :param: study_id, id of the study
    :type: integer
    :param: user, user that did the modification of parameters
    :type: integer
    :param: datasets_mapping, namespace+parameter to connector_id+dataset_id+parameter mapping
    :type: dict
    """
    try:

        # Retrieve study_manager
        study_manager = study_case_cache.get_study_case(study_id, False)

        
        # Launch load study-case with new parameters from dataset
        if notification_id not in study_manager.dataset_export_status_dict.keys():
            
            # check that the study is not loading
            if study_manager.load_status != LoadStatus.IN_PROGESS:
                study_manager.dataset_export_status_dict[notification_id] = LoadStatus.IN_PROGESS
                # Deserialize mapping
                datasets_mapping_deserialized = DatasetsMapping.deserialize(datasets_mapping)

                threading.Thread(
                    target=study_case_manager_export_from_dataset_mapping,
                    args=(study_manager, datasets_mapping_deserialized, notification_id),
                ).start()
            else:
                raise Exception("study case is currently loading, please retry the export at the end of the loading.")
        # deal with errors
        elif study_manager.dataset_export_status_dict[notification_id]  == LoadStatus.IN_ERROR:
            if notification_id in study_manager.dataset_export_error_dict.keys():
                raise Exception(study_manager.dataset_export_error_dict[notification_id])
            else:
                raise Exception("Error while exporting parameters in dataset")

        # return the status of the export
        return study_manager.dataset_export_status_dict.get(notification_id, LoadStatus.NONE)

    except DatasetsMappingException as exception :
        # Releasing study
        study_case_cache.release_study_case(study_id)
        app.logger.exception(
            f"Error when updating in background (from datasets mapping) {study_manager.study.name}:{exception}")
        raise exception
    except Exception as error:
        # Releasing study
        study_case_cache.release_study_case(study_id)
        raise StudyCaseError(error)

def get_dataset_import_error_message(study_id):
    """
    Retrieve study manager dataset load error in cache
    """
    # Retrieve study_manager
    study_manager = study_case_cache.get_study_case(study_id, False)
    return study_manager.dataset_load_error


def get_dataset_export_status(study_id, notification_id):
    """
    Retrieve study manager dataset export status in cache
    """
    # Retrieve study_manager
    study_manager = study_case_cache.get_study_case(study_id, False)
    return study_manager.dataset_export_status_dict.get(notification_id, LoadStatus.NONE)


def get_dataset_export_error_message(study_id, notification_id):
    """
    Retrieve study manager dataset export error in cache
    """
    # Retrieve study_manager
    study_manager = study_case_cache.get_study_case(study_id, False)
    return study_manager.dataset_export_error_dict.get(notification_id, "")


def update_study_parameters(study_id, user, files_list, file_info, parameters_to_save, columns_to_delete):
    """
    Configure the study case in the data manager or dump the study case on disk from a parameters list
    :param: study_id, id of the study
    :type: integer
    :param: user, user that did the modification of parameters
    :type: integer
    :param: files_list, list of files to be modified
    :type: list of file streams
    :param: file_info, list of information of files into files_list
    :type: dictionary with notification change data on each file
    :param: parameters_to_save, list of parameters that changed
    :type: dictionary of parameters data
    """
    user_fullname = f"{user.firstname} {user.lastname}"
    user_department = user.department
    user_id = user.id

    try:
        study_manager = study_case_cache.get_study_case(study_id, True)

        # Create notification
        if parameters_to_save != [] or files_list is not None or columns_to_delete != []:
            # Add notification to database
            new_notification_id = add_notification_db(study_id, user, UserCoeditionAction.SAVE, CoeditionMessage.SAVE)

        if files_list is not None:
            for file in files_list:
                # Converted file stream to a data frame
                # Write temporarly the received file
                tmp_folder = gettempdir()
                file_name = secure_filename(file.filename)
                file_path = join(tmp_folder, file_name)
                file.save(file_path)

                # Create a dataframe from it
                value = pd.read_csv(file_path, na_filter=False)

                # Convert string to Python type if possible (list, tuple,
                # etc..)
                value = value.applymap(isevaluatable)

                # Delete file
                remove(file_path)

                # Check column of dataframe
                column_to_delete_str = ""
                if columns_to_delete:
                    columns_list_from_csv = value.columns.tolist()
                    # Check if the targeted columns are still in the dataframe of the csv
                    contains_all_column = all(column in columns_list_from_csv for column in columns_to_delete)
                    column_to_delete_str = ",".join(columns_to_delete)
                    if contains_all_column:
                        raise ValueError(f'The columns "{column_to_delete_str}" you want to delete are still present in the dataframe')

                # Add file to parameters_to_save
                parameters_to_save.append(
                    {"variableId": file_info[file.filename]["variable_id"],
                     "columnDeleted": column_to_delete_str,
                     "newValue": value,
                     "namespace": file_info[file.filename]["namespace"],
                     "discipline": file_info[file.filename]["discipline"],
                     "changeType": StudyCaseChange.CSV_CHANGE})

                # Retrieving old file value
                old_value_stream = get_file_stream(
                    study_id, file_info[file.filename]["variable_id"])

                old_value_bytes = None
                if old_value_stream is not None:
                    old_value_bytes = old_value_stream.getvalue()

                # Add change to database
                add_change_db(new_notification_id,  # pylint: disable=possibly-used-before-assignment
                              file_info[file.filename]["variable_id"],
                              StudyCaseChange.CSV_CHANGE,
                              column_to_delete_str,
                              StudyCaseChange.CSV_CHANGE,
                              None,
                              None,
                              old_value_bytes,
                              datetime.now(),
                              None,
                              None,
                              None,
                              None,
                              None)

        values = {}
        for parameter in parameters_to_save:
            uuid_param = study_manager.execution_engine.dm.data_id_map[parameter["variableId"]]

            if uuid_param in study_manager.execution_engine.dm.data_dict:
                parameter_dm_data_dict = study_manager.execution_engine.dm.data_dict.get(
                    uuid_param, {})
                value = parameter["newValue"]
                parameter_type = parameter_dm_data_dict["type"]

                if parameter_type == ProxyDiscipline.PROC_BUILDER_MODAL:

                    proc_builder_value = ProcessBuilderParameterType.create(
                        value)

                    if proc_builder_value.has_usecase:
                        if proc_builder_value.has_valid_study_identifier:
                            local_scm = StudyCaseManager(
                                proc_builder_value.usecase_identifier)
                            loaded_values = local_scm.setup_usecase()

                            if len(loaded_values) > 0:
                                proc_builder_value.usecase_data = loaded_values[0]

                        elif proc_builder_value.usecase_type == "Reference":
                            reference_basepath = Config().reference_root_dir

                            # Build reference folder base on study process name and
                            # repository
                            reference_folder = join(
                                reference_basepath, proc_builder_value.process_repository,
                                proc_builder_value.process_name, proc_builder_value.usecase_name)

                            loaded_values = StudyCaseManager.static_load_raw_data(
                                reference_folder, DirectLoadDump())

                            proc_builder_value.usecase_data = loaded_values

                        elif proc_builder_value.usecase_type == "UsecaseData":

                            loaded_values = StudyCaseManager.static_load_raw_usecase_data(
                                proc_builder_value.process_repository,
                                proc_builder_value.process_name,
                                proc_builder_value.usecase_name)

                            proc_builder_value.usecase_data = loaded_values

                    value = proc_builder_value.to_data_manager_dict()

                # If value is dataframe make check about targeted type
                elif isinstance(value, pd.DataFrame):
                    parameter_type = parameter_dm_data_dict["type"]

                    if "array" in parameter_type:
                        # In case of array (mono dimensional) take the dataframe first
                        # column
                        value = value.iloc[:, 0].values
                    if "list" in parameter_type:
                        # In case of array (mono dimensional) take the dataframe first
                        # column
                        value = list(value.iloc[:, 0].values)
                    elif "dict" in parameter_type:
                        # Changes 12/09/20022
                        # Check if it is a "simple" dict or if it has subtype
                        parameter_subtype = parameter_dm_data_dict.get(
                            "subtype_descriptor", {"dict": None})
                        # Case when it is a dict of dataframe (same treatment
                        # as previous df_dict type)
                        if parameter_subtype == {"dict": "dataframe"}:
                            keys = list(set(value["variable"]))
                            columns = list(value.columns)
                            columns.remove("variable")
                            df_dict = {}
                            for key in keys:
                                df_dict[key] = value[columns][value["variable"] == key].reset_index(
                                    drop=True)
                            value = df_dict
                        else:
                            # Other subtype descriptors are not yet handled specifically so they are treated
                            # as simple dict
                            # Converting column to str
                            value["variable"] = value.variable.astype(str)
                            # In case of dict convert the dataframe to dict
                            value = value.set_index("variable")[
                                "value"].to_dict()
                    elif "dataframe_descriptor" in parameter_dm_data_dict.keys() and \
                                parameter_dm_data_dict["dataframe_descriptor"] is not None:

                        df_descriptor = parameter_dm_data_dict["dataframe_descriptor"]
                        if columns_to_delete != []:
                            columns = set(df_descriptor.keys()).intersection(columns_to_delete)
                            if columns is not None:
                                for column in columns:
                                    dataframe_descriptor = df_descriptor.get(column)
                                    if len(dataframe_descriptor) == 4 and dataframe_descriptor[3] is True:
                                        df_descriptor.pop(column)
                                    else:
                                        raise ValueError(f'The column "{column}" is not removable')
                        for colname in df_descriptor.keys():
                            type = df_descriptor[colname]
                            if type[0] == "array":
                                list_array = []
                                for row in list(value[colname]):
                                    list_array.append(array(row))

                                value[colname] = tuple(list_array)
                else:
                    # Add standard parameter change
                    try:
                        add_change_db(new_notification_id,
                                      parameter["variableId"],
                                      parameter_dm_data_dict["type"],
                                      parameter["columnDeleted"],
                                      parameter["changeType"],
                                      str(parameter["newValue"]),
                                      str(parameter["oldValue"]),
                                      None,
                                      datetime.now(),
                                      None,
                                      None,
                                      None,
                                      None,
                                      None)
                    except Exception as error:
                        app.logger.exception(f"Study change database insertion error: {error}")
                values[parameter["variableId"]] = value

                # Invalidate all linked validation discipline
                invalidate_namespace_after_save(study_manager.study.id, user_fullname, user_department,
                                                parameter["namespace"])

        if study_manager.load_status != LoadStatus.IN_PROGESS:
            study_manager.clear_error()
            study_manager.load_status = LoadStatus.IN_PROGESS
            threading.Thread(
                target=study_case_manager_update, args=(study_manager, values, False, False)).start()

        if study_manager.load_status == LoadStatus.IN_ERROR:
            raise Exception(study_manager.error_message)

        # Releasing study
        study_case_cache.release_study_case(study_id)

        # Return logical treeview coming from execution engine
        loaded_study_case = LoadedStudyCase(
            study_manager, False, False, user_id)

         #get execution status
        study_case = StudyCase.query.filter(StudyCase.id == study_id).first()
        if study_case is not None and study_case.current_execution_id is not None:
            study_case_execution = StudyCaseExecution.query.filter(StudyCaseExecution.id == study_case.current_execution_id).first()
            loaded_study_case.study_case.execution_status = study_case_execution.execution_status


        return loaded_study_case

    except Exception as error:
        # Releasing study
        study_case_cache.release_study_case(study_id)

        raise StudyCaseError(error)


def delete_study_cases(studies):
    """
    Delete one or multiple study cases from database and disk
    :param: studies, list of studycase ids to be deleted
    :type: list of integers
    """
    # Verify that we find same number of studies by querying database
    with app.app_context():
        query = StudyCase.query.filter(StudyCase.id.in_(
            studies)).all()

        if len(query) == len(studies):
            try:
                for sc in query:
                    db.session.delete(sc)

                    # Delete study from cache if it exist
                    study_case_cache.delete_study_case_from_cache(sc.id)

                db.session.commit()
            except Exception as ex:
                db.session.rollback()
                raise ex

            # Once removed from db, remove it from file system
            for study in query:
                folder = StudyCaseManager.get_root_study_data_folder(
                    study.group_id, study.id)
                rmtree(folder, ignore_errors=True)

            return f"All the studies (identifier(s) {studies}) have been deleted in the database"
        else:
            raise InvalidStudy("Unable to find all the study cases to delete in the database, "
                               "please refresh your study cases list")


def get_file_stream(study_id, parameter_key):
    """
    get file stream from a study file parameter
    :param: study_id, id of the study
    :type: integer
    :param: parameter_key, key of the parameter to retrieve
    :type: string
    """
    study_manager = study_case_cache.get_study_case(study_id, False)
    if study_manager.load_status == LoadStatus.LOADED:
        uuid_param = study_manager.execution_engine.dm.data_id_map[parameter_key]
        if uuid_param in study_manager.execution_engine.dm.data_dict:
            try:
                file_read_bytes = study_manager.execution_engine.dm.get_parameter_data(
                    parameter_key)
            except Exception as error:
                raise InvalidFile(
                    f"The following file {parameter_key}.csv raise this error while trying to read it : {error}")
            return file_read_bytes

        else:
            raise StudyCaseError(
                f"Parameter {parameter_key} does not exist in this study case")
    else:
        # if the study is not loaded yet, read the pickle file directly to get
        # the value
        try:
            parameters = study_manager.get_parameter_data(parameter_key)
            return parameters
        except Exception as error:
            raise InvalidFile(
                f"The study read only data are not accessible : {error}")


def get_study_data_stream(study_id):
    """
    export data in a zip file and return its path
    :param: study_id, id of the study to export
    :type: integer
    """
    study_manager = study_case_cache.get_study_case(study_id, False)

    try:
        tmp_folder = gettempdir()
        file_name = secure_filename(f"{study_manager.study.name}")
        file_path = join(tmp_folder, file_name)
        zip_path = study_manager.execution_engine.export_data_dict_and_zip(
            file_path)

    except Exception as error:
        raise InvalidFile(
            f"The following study file raise this error while trying to read it : {error}")
    return zip_path


def get_study_in_read_only_mode(study_id, no_data):
    """
    check if a study json file exists,
         if true, read loaded study case in read only mode, and return the json
         if false, return None, it will be checked on client side
     :param: study_id, id of the study to export
     :type: integer
     :param: no_data, if study is loaded with no data or not
     :type: boolean
    """
    study_manager = StudyCaseManager(study_id)
    if study_manager.check_study_case_json_file_exists():
        try:
            loaded_study_json = study_manager.read_loaded_study_case_in_json_file(
                no_data)
            # read dashboard and set it to the loaded study
            # (it takes less time to read it apart than to have the dashboard in the read only file)
            if len(loaded_study_json["post_processings"]) > 0:
                dashboard = study_manager.read_dashboard_in_json_file()
                loaded_study_json["dashboard"] = dashboard
            return loaded_study_json

        except Exception as error:
            app.logger.error(
                f"Study {study_id} readonly mode error while getting readonly file: {error}")
            return "null"
    else:
        return "null"


def get_study_dashboard_in_file(study_id):
    """
    check if a dashboard json file exists,
         if true, read dashboard file, and return the json
         if false, return None, it will be checked on client side
     :param: study_id, id of the study to export
     :type: integer
    """
    study_manager = StudyCaseManager(study_id)
    if study_manager.check_dashboard_json_file_exists():
        try:
            dashboard = study_manager.read_dashboard_in_json_file()
            return dashboard

        except Exception as error:
            app.logger.error(
                f"Study {study_id} dashboard error while reading file: {error}")
            return "null"
    else:
        return "null"


def get_study_data_file_path(study_id) -> str:
    """
    Return file path where study has stored its data

    :param study_id: id of the study to export
    :type study_id: integer

    """
    study_manager = study_case_cache.get_study_case(study_id, False)

    try:
        data_file_path = study_manager.study_data_file_path

    except Exception as error:
        raise InvalidFile(
            f"The following study file raise this error while trying to read it : {error}")
    return data_file_path


def set_study_data_file(study_identifier, files_list):
    """
    Set study data file (overwrite the existing ones)
    :param study_identifier: study identifier
    :type study_identifier: int
    :param files_list: study file to install
    :type files_list: list of file streams
    """
    # Check expected mandatory file
    filenames = list(files_list.keys())

    if DataSerializer.pkl_filename not in filenames or DataSerializer.disc_status_filename not in filenames:
        raise StudyCaseError("Missing mandatory data")

    # Check study is not running
    study_calculation_status = calculation_status(study_identifier)

    if study_calculation_status.study_case_execution_status == StudyCaseExecution.RUNNING:
        raise StudyCaseError("Cannot update data of a running study")

    study_case_manager = StudyCaseManager(study_identifier)

    # Manager overwrite of dm.pkl
    dm_file = files_list[DataSerializer.pkl_filename]
    dm_file.save(study_case_manager.study_data_file_path)

    # Manage overwrite of disciplines_status.pkl
    disciplines_status_file = files_list[DataSerializer.disc_status_filename]
    disciplines_status_file.save(study_case_manager.study_discipline_file_path)

    # Manage overwrite of cache.pkl (optional)
    cache_file = files_list.get(DataSerializer.cache_filename, None)
    if cache_file is not None:
        cache_file.save(study_case_manager.study_cache_file_path)

    if study_case_cache.is_study_case_cached(study_identifier):
        study_case_cache.delete_study_case_from_cache(study_identifier)

    # Get date
    modify_date = datetime.now().astimezone(timezone.utc).replace(tzinfo=None)
    study_case = StudyCase.query.filter(
        StudyCase.id == study_identifier).first()
    study_case.modification_date = modify_date
    db.session.add(study_case)
    db.session.commit()


def copy_study_discipline_data(study_id, discipline_from, discipline_to):
    """
    Copy discipline data from a discipline to another
    :param: study_id, id of the study
    :type: integer
    :param: discipline_from, name of the discipline to copy
    :type: string
    :param: discipline_to, name of the discipline to update
    :type: string
    """
    study_manager = study_case_cache.get_study_case(study_id, False)
    # Check if each discipline key exisit in the current study case
    if discipline_from in study_manager.execution_engine.dm.disciplines_dict and discipline_to \
            in study_manager.execution_engine.dm.disciplines_dict:

        results = {}

        # Retrieve inputs data from the two disciplines using the datamanger dictionary to take into account
        # parameter visibility aspects

        for key, value in study_manager.execution_engine.dm.data_dict.items():

            if key.startswith(discipline_from):

                # Extract parameter name to update target discipline
                from_parameter_name = key.replace(f"{discipline_from}.", "")

                # Build target parameter
                to_parameter_key = f"{discipline_to}.{from_parameter_name}"
                uuid_param = study_manager.execution_engine.dm.data_id_map[to_parameter_key]
                if uuid_param in study_manager.execution_engine.dm.data_dict:
                    study_manager.execution_engine.dm.data_dict[uuid_param][DataManager.VALUE] = value[
                        DataManager.VALUE]

                    results[uuid_param] = study_manager.execution_engine.dm.data_dict[uuid_param]

        return results

    else:
        raise StudyCaseError(
            f"One those two disciplines '{discipline_from}' or '{discipline_from}' does not exist in this study case")


def clean_database_with_disabled_study_case(logger=None):
    """
    Method that delete all study case that have been flag disabledS_REPOSITORY' key

    @param logger: logging message
    @type Logger

    """
    study_list = StudyCase.query.filter(StudyCase.disabled).all()

    logger.info(f"{len(study_list)} study disabled found")

    if len(study_list) > 0:
        study_identifiers = list(map(lambda s: s.id, study_list))
        logger.info(f"Study case identifier to remove: {study_identifiers}")

        delete_study_cases(study_identifiers)

def save_study_is_active(study_id):
    """
    Save the date of the last use of the study in case of micro-service server mode
    """
    if Config().server_mode == Config.CONFIG_SERVER_MODE_K8S:
        if study_case_cache.update_study_case_last_active_date(study_id):
            save_study_last_active_date(study_id, datetime.now())


def check_study_is_still_active_or_kill_pod():
    """
    Check that the last date of the study is alive is less than a timespan last_hours in hours defined in the request
    If not, the allocation, service and deployment of the current study is deleted
    """
    with app.app_context():
        config = Config()
        last_hours = config.study_pod_delay
        app.logger.debug(f"Start check on active study pod since {last_hours} hour(s)")

        if config.server_mode == Config.CONFIG_SERVER_MODE_K8S and last_hours is not None :
            #delete allocation in db

            inactive_studies = []
            try:
                inactive_studies =  check_studies_last_active_date(last_hours, app.logger)
            except Exception as ex:
                app.logger.error(f"Error wile checking the last active date in file: {ex}")
                raise ex
            allocations_to_delete = []
            for study_id in inactive_studies:
                app.logger.info(f"Delete pod and allocation for study {study_id}")

                #delete the file
                delete_study_last_active_file(study_id)
                # get associated allocation to the study
                allocation = PodAllocation.query.filter(PodAllocation.identifier == study_id).filter(PodAllocation.pod_type == PodAllocation.TYPE_STUDY).first()
                allocations_to_delete.append(allocation)
            #delete service and deployment (that will delete the pod)
            delete_study_server_services_and_deployments(allocations_to_delete)


def get_markdown_documentation(study_id, discipline_key):
    spec = importlib.util.find_spec(discipline_key)
    # for the doc of a process, spec.origin = process_folder\__init__.py
    if '__init__.py' in spec.origin:
        filepath = spec.origin.split('__init__.py')[0]
    else:
        # for the doc of a discipline, spec.origin = discipline_folder\discipline_name.py
        filepath = spec.origin.split('.py')[0]
    markdown_data = TreeNode.get_markdown_documentation(filepath)
    return markdown_data