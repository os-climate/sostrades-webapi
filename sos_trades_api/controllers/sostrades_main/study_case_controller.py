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
from flask import jsonify

from sos_trades_api.controllers.sostrades_data.study_case_controller import add_last_opened_study_case

"""
mode: python; py-indent-offset: 4; tab-width: 4; coding: utf-8
Study case Functions
"""

import os
import time

from sqlalchemy import desc
from sos_trades_core.execution_engine.sos_discipline import SoSDiscipline
import traceback
import sys
import pandas as pd
from os.path import join
from tempfile import gettempdir
from os import remove
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
import shutil
from shutil import rmtree

from sos_trades_api.tools.code_tools import isevaluatable
from sos_trades_api.tools.data_graph_validation.data_graph_validation import invalidate_namespace_after_save
from sos_trades_core.execution_engine.data_manager import DataManager
from sos_trades_core.tools.tree.serializer import DataSerializer
from sos_trades_core.tools.proc_builder.process_builder_parameter_type import ProcessBuilderParameterType
from sos_trades_api.config import Config
from sos_trades_api.server.base_server import db, app, study_case_cache

from sos_trades_api.tools.coedition.coedition import add_notification_db, UserCoeditionAction, add_change_db
from sos_trades_api.models.loaded_study_case import LoadedStudyCase
from sos_trades_api.models.database_models import StudyCase, StudyCaseChange, AccessRights, StudyCaseExecution, User, \
    ReferenceStudy
from sos_trades_api.controllers.sostrades_data.calculation_controller import calculation_status
from sos_trades_core.tools.rw.load_dump_dm_data import DirectLoadDump
from sos_trades_api.models.study_case_dto import StudyCaseDto
from sos_trades_api.controllers.sostrades_data.ontology_controller import load_processes_metadata, \
    load_repositories_metadata
import threading
from sos_trades_api.tools.loading.loading_study_and_engine import study_case_manager_loading, \
    study_case_manager_update, study_case_manager_loading_from_reference, \
    study_case_manager_loading_from_usecase_data, \
    study_case_manager_loading_from_study
from sos_trades_api.controllers.error_classes import StudyCaseError, InvalidStudy, InvalidFile
from sos_trades_api.tools.loading.study_case_manager import StudyCaseManager
from sos_trades_api.models.loaded_study_case import LoadStatus
from numpy import array


def create_study_case(user_id, study_case_identifier, reference, from_type=None):
    """
    Create a study case for the user, adding reference data if specified
    """
    status = StudyCaseExecution.NOT_EXECUTED

    try:

        study_case_manager = study_case_cache.get_study_case(study_case_identifier, False)

        study_case = None
        with app.app_context():
            study_case = StudyCase.query.filter(StudyCase.id == study_case_identifier).first()

        if from_type == 'Reference':

            # Get reference path
            reference_path = f'{study_case.repository}.{study_case.process}.{reference}'

            # Generate execution status
            reference_study = ReferenceStudy.query.filter(ReferenceStudy.name == reference) \
                .filter(ReferenceStudy.reference_path == reference_path).first()
            if reference_study is not None:
                user = User.query.filter(User.id == user_id).first()
                status = reference_study.execution_status

                if reference_study.execution_status == ReferenceStudy.UNKNOWN:
                    status = StudyCaseExecution.NOT_EXECUTED

                new_study_case_execution = StudyCaseExecution()
                new_study_case_execution.study_case_id = study_case.id
                new_study_case_execution.execution_status = status
                new_study_case_execution.creation_date = datetime.now().astimezone(timezone.utc).replace(
                    tzinfo=None)
                new_study_case_execution.requested_by = user.username
                db.session.add(new_study_case_execution)
                db.session.commit()

                study_case.current_execution_id = new_study_case_execution.id
                db.session.add(study_case)
                db.session.commit()

        # Persist data using the current persistence strategy
        study_case_manager.dump_data(study_case_manager.dump_directory)
        study_case_manager.dump_disciplines_data(study_case_manager.dump_directory)

        # Loading data for study created empty
        if reference is None:

            study_case_manager.load_status = LoadStatus.LOADED
            study_case_manager.n2_diagram = {}
            study_case_manager.execution_engine.dm.treeview = None
            study_case_manager.execution_engine.get_treeview(False, False)

        # Adding reference data and loading study data
        else:
            if from_type == 'Reference':

                reference_basepath = Config().reference_root_dir

                # Build reference folder base on study process name and
                # repository
                reference_folder = join(
                    reference_basepath, study_case.repository, study_case.process, reference)

                # Get ref generation ID associated to this ref
                reference_identifier = f'{study_case.repository}.{study_case.process}.{reference}'

                if study_case_manager.load_status != LoadStatus.IN_PROGESS and study_case_manager.load_status != LoadStatus.LOADED:
                    study_case_manager.load_status = LoadStatus.IN_PROGESS

                    threading.Thread(
                        target=study_case_manager_loading_from_reference,
                        args=(study_case_manager, False, False, reference_folder, reference_identifier)).start()

            elif from_type == 'UsecaseData':

                if study_case_manager.load_status == LoadStatus.NONE:
                    study_case_manager.load_status = LoadStatus.IN_PROGESS

                    threading.Thread(
                        target=study_case_manager_loading_from_usecase_data,
                        args=(study_case_manager, False, False, study_case.repository, study_case.process, reference)).start()

        if study_case_manager.load_status == LoadStatus.IN_ERROR:
            raise Exception(study_case_manager.error_message)
        loaded_study_case = LoadedStudyCase(study_case_manager, False, False, user_id)

        process_metadata = load_processes_metadata(
            [f'{loaded_study_case.study_case.repository}.{loaded_study_case.study_case.process}'])

        repository_metadata = load_repositories_metadata(
            [loaded_study_case.study_case.repository])

        loaded_study_case.study_case.apply_ontology(
            process_metadata, repository_metadata)

        # Update cache modification date and release study
        study_case_cache.update_study_case_modification_date(
            loaded_study_case.study_case.id, loaded_study_case.study_case.modification_date)

        # Modifying study case to add access right of creator (Manager)
        loaded_study_case.study_case.is_manager = True

        if not loaded_study_case.study_case.execution_status or loaded_study_case.study_case.execution_status == SoSDiscipline.STATUS_CONFIGURE:
            loaded_study_case.study_case.execution_status = StudyCaseExecution.NOT_EXECUTED
        else:
            loaded_study_case.study_case.execution_status = status
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        study_case_manager.set_error(''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)), True)

        # Then propagate exception
        raise Exception(study_case_manager.error_message)

    return loaded_study_case


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


def load_study_case(study_id, study_access_right, user_id, reload=False):
    """
    Retrieve all the study cases shared groups names list from user_id
    :params: study_id, id of the study to load
    :type: integer
    :params: study_access_right, information about the access right needed for the study
    :type: AccessRights enum
    :params: user_id, user id that want to access the study (to get preferences)
    :type: integer
    :params: reload, indicates if the study must be reloaded, false by default
    :type: boolean
    """

    start_time = time.time()
    study_manager = study_case_cache.get_study_case(study_id, False)

    cache_duration = time.time() - start_time
    if reload:
        study_manager.study_case_manager_reload_backup_files()
        study_manager.reset()

    read_only = study_access_right == AccessRights.COMMENTER
    no_data = study_access_right == AccessRights.RESTRICTED_VIEWER

    launch_load_study_in_background(study_manager,  no_data, read_only)

    if study_manager.load_status == LoadStatus.IN_ERROR:
        raise Exception(study_manager.error_message)

    loaded_study_case = LoadedStudyCase(study_manager, no_data, read_only, user_id)
    loading_duration = time.time() - start_time

    app.logger.info(f'load_study_case {study_id}, get cache: {cache_duration}')
    app.logger.info(f'load_study_case {study_id}, loading:{loading_duration} ')

    # 22-09-2022: Update: add Read_only_mode as it is loaded so that after a study creation,
    # if the study is DONE, the study is opened in read only
    if study_manager.load_status == LoadStatus.LOADED:
        process_metadata = load_processes_metadata(
            [f'{loaded_study_case.study_case.repository}.{loaded_study_case.study_case.process}'])

        repository_metadata = load_repositories_metadata(
            [loaded_study_case.study_case.repository])

        loaded_study_case.study_case.apply_ontology(
            process_metadata, repository_metadata)

        if study_access_right == AccessRights.MANAGER:
            loaded_study_case.study_case.is_manager = True
        elif study_access_right == AccessRights.CONTRIBUTOR:
            loaded_study_case.study_case.is_contributor = True
        elif study_access_right == AccessRights.COMMENTER:
            loaded_study_case.study_case.is_commenter = True
        else:
            loaded_study_case.study_case.is_restricted_viewer = True
        end_loading_duration = time.time() - start_time

        # Read dashboard and set it to the loaded studycase
        # If the root process is at done
        if study_manager.execution_engine.root_process.status == SoSDiscipline.STATUS_DONE:
            loaded_study_case.dashboard = get_study_dashboard_in_file(study_id)

        end_dashboard_duration = time.time() - start_time
        app.logger.info(f'load_study_case {study_id}, end loading:{end_loading_duration} ')
        app.logger.info(f'load_study_case {study_id}, dashboard:{end_dashboard_duration} ')

        # Add this study in last study opened in database
        add_last_opened_study_case(study_id, user_id)

    # Return logical treeview coming from execution engine
    return loaded_study_case

def launch_load_study_in_background(study_manager,  no_data, read_only):
    """
    Launch only the background thread
    """
    if study_manager.load_status == LoadStatus.NONE:
        study_manager.load_status = LoadStatus.IN_PROGESS
        threading.Thread(
            target=study_case_manager_loading, args=(study_manager, no_data, read_only)).start()

def load_study_case_with_read_only_mode(study_id, study_access_right, user_id):
     # Proceeding after rights verification
    # Get readonly file, in case of a restricted viewer get with no_data
    study_json = get_study_in_read_only_mode(study_id, study_access_right == AccessRights.RESTRICTED_VIEWER)

    # check in read only file that the study status is DONE
    if study_json is not None and study_json != 'null':
        study_case_value = study_json.get('study_case')
        if study_case_value is not None :
            execution_status = study_case_value.get("execution_status")
            #if the study status is DONE, the study must be opened in readonly mode
            if execution_status == SoSDiscipline.STATUS_DONE:
                # launch the loading in background
                study_manager = study_case_cache.get_study_case(study_id, False)
                read_only = study_access_right == AccessRights.COMMENTER
                no_data = study_access_right == AccessRights.RESTRICTED_VIEWER
                launch_load_study_in_background(study_manager,  no_data, read_only)
                #set study access rights
                if study_access_right == AccessRights.MANAGER:
                    study_json['study_case']['is_manager'] = True
                elif study_access_right == AccessRights.CONTRIBUTOR:
                    study_json['study_case']['is_contributor'] = True
                elif study_access_right == AccessRights.COMMENTER:
                    study_json['study_case']['is_commenter'] = True
                else:
                    study_json['study_case']['is_restricted_viewer'] = True

                # Add this study in last study opened in database
                add_last_opened_study_case(study_id, user_id)

                return study_json

    # If the study is not in read only mode, it is normally loaded
    loaded_study = load_study_case(study_id, study_access_right, user_id)

    return jsonify(loaded_study)


def copy_study_case(study_id, source_study_case_identifier, user_id):
    """ copy an existing study case with a new name
    :param study_id: study case identifier to modify
    :type study_id:  integer
    :param source_study_case_identifier: identifier of the study case to copy
    :type source_study_case_identifier: int
    :param user_id:  id user owner of the new study case
    :type user_id: integer
    """
    with app.app_context():
        study_manager_source = study_case_cache.get_study_case(
            source_study_case_identifier, False)

        # Copy the last study case execution and then update study_id, creation date and request_by.
        study_execution = StudyCaseExecution.query.filter(StudyCaseExecution.study_case_id == source_study_case_identifier) \
            .order_by(desc(StudyCaseExecution.id)).first()

        user = User.query.filter(User.id == user_id).first()

        status = StudyCaseExecution.NOT_EXECUTED

        study_case = StudyCase.query.filter(StudyCase.id == study_id).first()

        if study_execution is not None:

            if study_execution.execution_status == StudyCaseExecution.RUNNING \
                    or study_execution.execution_status == StudyCaseExecution.STOPPED \
                    or study_execution.execution_status == StudyCaseExecution.PENDING:
                status = StudyCaseExecution.NOT_EXECUTED
            else:
                status = study_execution.execution_status

            new_study_execution = StudyCaseExecution()
            new_study_execution.study_case_id = study_case.id
            new_study_execution.execution_status = status
            new_study_execution.execution_type = study_execution.execution_type
            new_study_execution.requested_by = user.username

            db.session.add(new_study_execution)
            db.session.commit()

            study_case.current_execution_id = new_study_execution.id
            db.session.add(study_case)
            db.session.commit()

        # result structure
        result = None

        try:
            study_manager = study_case_cache.get_study_case(
                study_case.id, False)

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

            result = StudyCaseDto(study_case)

            process_metadata = load_processes_metadata(
                [f'{study_case.repository}.{study_case.process}'])
            repository_metadata = load_repositories_metadata(
                [study_case.repository])

            result.apply_ontology(process_metadata, repository_metadata)
            result.execution_status = status
            # Modifying study case to add access right of creator (Manager)
            result.is_manager = True

        except:

            exc_type, exc_value, exc_traceback = sys.exc_info()
            study_manager.set_error(''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)))

            # Then propagate exception
            raise Exception(study_manager.error_message)

        return result


def update_study_parameters(study_id, user, files_list, file_info, parameters_to_save):
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

    user_fullname = f'{user.firstname} {user.lastname}'
    user_department = user.department
    user_id = user.id

    try:
        study_manager = study_case_cache.get_study_case(
            study_id, True)

        # Create notification
        if parameters_to_save != [] or files_list != None:
            # Add notification to database
            new_notification_id = add_notification_db(study_id, user,
                                                      UserCoeditionAction.SAVE)

        if files_list != None:
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
                # Add file to parameters_to_save
                parameters_to_save.append(
                    {'variableId': file_info[file.filename]['variable_id'],
                     'newValue': value,
                     'namespace': file_info[file.filename]['namespace'],
                     'discipline': file_info[file.filename]['discipline'],
                     'changeType': StudyCaseChange.CSV_CHANGE})

                # Retrieving old file value
                old_value_stream = get_file_stream(
                    study_id, file_info[file.filename]['variable_id'])

                old_value_bytes = None
                if old_value_stream is not None:
                    old_value_bytes = old_value_stream.getvalue()

                # Add change to database
                add_change_db(new_notification_id,
                              file_info[file.filename]['variable_id'],
                              StudyCaseChange.CSV_CHANGE,
                              StudyCaseChange.CSV_CHANGE,
                              None,
                              None,
                              old_value_bytes,
                              datetime.now())

        values = {}
        connectors = {}
        for parameter in parameters_to_save:
            uuid_param = study_manager.execution_engine.dm.data_id_map[parameter['variableId']]

            if uuid_param in study_manager.execution_engine.dm.data_dict:
                parameter_dm_data_dict = study_manager.execution_engine.dm.data_dict.get(uuid_param,{})
                value = parameter['newValue']
                parameter_type = parameter_dm_data_dict['type']

                if parameter_type == SoSDiscipline.PROC_BUILDER_MODAL:

                    proc_builder_value = ProcessBuilderParameterType.create(value)

                    if proc_builder_value.has_usecase:
                        if proc_builder_value.has_valid_study_identifier:
                            local_scm = StudyCaseManager(proc_builder_value.usecase_identifier)
                            loaded_values = local_scm.setup_usecase()

                            if len(loaded_values) > 0:
                                proc_builder_value.usecase_data = loaded_values[0]

                        elif proc_builder_value.usecase_type == 'Reference':
                            reference_basepath = Config().reference_root_dir

                            # Build reference folder base on study process name and
                            # repository
                            reference_folder = join(
                                reference_basepath, proc_builder_value.process_repository,
                                proc_builder_value.process_name, proc_builder_value.usecase_name)

                            loaded_values = StudyCaseManager.static_load_raw_data(reference_folder, DirectLoadDump())

                            proc_builder_value.usecase_data = loaded_values

                        elif proc_builder_value.usecase_type == 'UsecaseData':

                            loaded_values = StudyCaseManager.static_load_raw_usecase_data(
                                proc_builder_value.process_repository,
                                proc_builder_value.process_name,
                                proc_builder_value.usecase_name)

                            proc_builder_value.usecase_data = loaded_values

                    value = proc_builder_value.to_data_manager_dict()

                # If value is dataframe make check about targeted type
                elif isinstance(value, pd.DataFrame):
                    parameter_type = parameter_dm_data_dict['type']

                    if 'array' in parameter_type:
                        # In case of array (mono dimensional) take the dataframe first
                        # column
                        value = value.iloc[:, 0].values

                    elif 'dict' in parameter_type:
                        # Changes 12/09/20022
                        # Check if it is a "simple" dict or if it has subtype
                        parameter_subtype = parameter_dm_data_dict.get('subtype_descriptor',{'dict':None})
                        # Case when it is a dict of dataframe (same treatment as previous df_dict type)
                        if parameter_subtype == {'dict': 'dataframe'}:
                            keys = list(set(value['variable']))
                            columns = list(value.columns)
                            columns.remove('variable')
                            df_dict = {}
                            for key in keys:
                                df_dict[key] = value[columns][value['variable'] == key].reset_index(drop=True)
                            value = df_dict
                        else:
                            # Other subtype descriptors are not yet handled specifically so they are treated
                            # as simple dict
                            # Converting column to str
                            value['variable'] = value.variable.astype(str)
                            # In case of dict convert the dataframe to dict
                            value = value.set_index('variable')['value'].to_dict()
                    else:
                        # dataframe, check array element types
                        if 'dataframe_descriptor' in parameter_dm_data_dict.keys() and \
                                parameter_dm_data_dict['dataframe_descriptor'] is not None:

                            df_descriptor = parameter_dm_data_dict['dataframe_descriptor']
                            for colname in df_descriptor.keys():
                                type = df_descriptor[colname]
                                if type[0] == "array":
                                    list_array =[]
                                    for row in list(value[colname]):
                                        list_array.append(array(row))

                                    value[colname] = tuple(list_array)
                else:
                    # Add standard parameter change
                    try:
                        add_change_db(new_notification_id,
                                      parameter['variableId'],
                                      parameter_dm_data_dict['type'],
                                      parameter['changeType'],
                                      str(parameter['newValue']),
                                      str(parameter['oldValue']),
                                      None,
                                      datetime.now())
                    except Exception as error:
                        app.logger.exception(
                            'Study change database insertion error')
                if parameter['changeType'] == StudyCaseChange.CONNECTOR_DATA_CHANGE:
                    connectors[parameter['variableId']] = value
                else:
                    values[parameter['variableId']] = value

                # Invalidate all linked validation discipline
                invalidate_namespace_after_save(study_manager.study.id, user_fullname, user_department,
                                                parameter['namespace'])

        if study_manager.load_status != LoadStatus.IN_PROGESS:
            study_manager.clear_error()
            study_manager.load_status = LoadStatus.IN_PROGESS
            threading.Thread(
                target=study_case_manager_update, args=(study_manager, values, False, False, connectors)).start()

        if study_manager.load_status == LoadStatus.IN_ERROR:
            raise Exception(study_manager.error_message)

        # Releasing study
        study_case_cache.release_study_case(study_id)

        # Return logical treeview coming from execution engine
        loaded_study_case = LoadedStudyCase(study_manager, False, False, user_id)

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
                folder = StudyCaseManager.get_root_study_data_folder(study.group_id, study.id)
                rmtree(folder, ignore_errors=True)

            return f'All the studies (identifier(s) {studies}) have been deleted in the database'
        else:
            raise InvalidStudy(f'Unable to find all the study cases to delete in the database, '
                               f'please refresh your study cases list')


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
                    f'The following file {parameter_key}.csv raise this error while trying to read it : {error}')
            return file_read_bytes

        else:
            raise StudyCaseError(
                f'Parameter {parameter_key} does not exist in this study case')
    else:
        # if the study is not loaded yet, read the pickle file directly to get the value
        try:
            parameters = study_manager.get_parameter_data(parameter_key)
            return parameters
        except Exception as error:
                raise InvalidFile(f'The study read only data are not accessible : {error}')

def get_study_data_stream(study_id):
    """
        export data in a zip file and return its path
        :param: study_id, id of the study to export
        :type: integer
    """
    study_manager = study_case_cache.get_study_case(study_id, False)

    try:
        tmp_folder = gettempdir()
        file_name = secure_filename(f'{study_manager.study.name}')
        file_path = join(tmp_folder, file_name)
        zip_path = study_manager.execution_engine.export_data_dict_and_zip(file_path)

    except Exception as error:
        raise InvalidFile(
            f'The following study file raise this error while trying to read it : {error}')
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
            loaded_study_json = study_manager.read_loaded_study_case_in_json_file(no_data)
            # read dashboard and set it to the loaded study
            # (it takes less time to read it apart than to have the dashboard in the read only file)
            if len(loaded_study_json["post_processings"]) > 0:
                dashboard = study_manager.read_dashboard_in_json_file()
                loaded_study_json['dashboard'] = dashboard
            return loaded_study_json

        except Exception as error:
            app.logger.error(
                        f'Study {study_id} readonly mode error while getting readonly file: {error}')
            return 'null'
    else:
        return 'null'

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
                        f'Study {study_id} dashboard error while reading file: {error}')
            return 'null'
    else:
        return 'null'

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
            f'The following study file raise this error while trying to read it : {error}')
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
        raise StudyCaseError('Missing mandatory data')

    # Check study is not running
    study_calculation_status = calculation_status(study_identifier)

    if study_calculation_status.study_case_execution_status == StudyCaseExecution.RUNNING:
        raise StudyCaseError('Cannot update data of a running study')

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
    study_case = StudyCase.query.filter(StudyCase.id == study_identifier).first()
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
                from_parameter_name = key.replace(f'{discipline_from}.', '')

                # Build target parameter
                to_parameter_key = f'{discipline_to}.{from_parameter_name}'
                uuid_param = study_manager.execution_engine.dm.data_id_map[to_parameter_key]
                if uuid_param in study_manager.execution_engine.dm.data_dict:
                    study_manager.execution_engine.dm.data_dict[uuid_param][DataManager.VALUE] = value[
                        DataManager.VALUE]

                    results[uuid_param] = study_manager.execution_engine.dm.data_dict[uuid_param]

        return results

    else:
        raise StudyCaseError(
            f'One those two disciplines \'{discipline_from}\' or \'{discipline_from}\' does not exist in this study case')


def clean_database_with_disabled_study_case(logger=None):
    """
    Method that delete all study case that have been flag disabledS_REPOSITORY' key

    @param logger: logging message
    @type Logger

    """

    study_list = StudyCase.query.filter(StudyCase.disabled == True).all()

    logger.info(f'{len(study_list)} study disabled found')

    if len(study_list) > 0:
        study_identifiers = list(map(lambda s: s.id, study_list))
        logger.info(f'Study case identifier to remove: {study_identifiers}')

        delete_study_cases(study_identifiers)





