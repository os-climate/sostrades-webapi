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
from datetime import datetime
from pathlib import Path

from sos_trades_api.controllers.error_classes import InvalidFile, StudyCaseError
from sos_trades_api.models.database_models import (
    AccessRights,
    PodAllocation,
    StudyCase,
    StudyCaseExecution,
)
from sos_trades_api.models.loaded_study_case import LoadedStudyCase, LoadStatus
from sos_trades_api.models.study_case_dto import StudyCaseDto
from sos_trades_api.server.base_server import app, study_case_cache
from sos_trades_api.tools.allocation_management.allocation_management import (
    get_allocation_status_by_study_id,
)
from sos_trades_api.tools.file_tools import write_object_in_json_file
from sos_trades_api.tools.loading.study_case_manager import StudyCaseManager


def check_study_has_read_only_mode(user_study: StudyCaseDto) -> bool:
    """
    Check read only file exists and study execution status at Finished
    """
    study_manager = StudyCaseManager(user_study.id)
    return study_manager.check_study_case_json_file_exists() and \
            user_study.execution_status == StudyCaseExecution.FINISHED
    

def check_and_clean_read_only_file(user_study: StudyCaseDto) -> bool:
    """
    Verify if a study case has a valid read-only file and manage associated files based on execution status.

    This function checks for the existence of 'loaded_study_case.json' and manages its presence
    based on the study's execution status. If the study is not in FINISHED state,
    it removes both 'loaded_study_case.json' and 'loaded_study_case_no_data.json' files.

    Args:
        user_study (StudyCaseDto): Study case data transfer object containing study information

    Returns:
        bool: True if the study has a valid read-only file and is in FINISHED state,
              False otherwise

    """
    try:
        file_exist = False
        study_manager = StudyCaseManager(user_study.id)
        # Check if paths and file exist
        if study_manager.check_study_case_json_file_exists():
            if user_study.execution_status == StudyCaseExecution.FINISHED:
                file_exist = True
            else:
                # If execution_status is not FINISHED, the loaded_study_case.json does not exist anymore
                try:
                    study_manager.delete_loaded_study_case_in_json_file()
                    app.logger.info(f"loaded_study_case.json for {user_study.id} has been deleted because his status is not Finished")
                except Exception as exp:
                    app.logger.error(f"Error while deletion of read only file for {user_study.id} because his status is not Finished: {str(exp)}")
        return file_exist
    except Exception as ex:
        raise Exception(f"Error processing study {user_study.id}: {ex}")


def get_read_only(study_case_identifier, study_access_right):
    # retrieve study execution status
    study_case = StudyCase.query.filter(StudyCase.id == study_case_identifier).first()

    is_read_only_possible = False
    loaded_study_case = None
    if study_case is not None and study_case.current_execution_id is not None:
        study_case_execution = StudyCaseExecution.query.filter(
            StudyCaseExecution.id == study_case.current_execution_id).first()
        # check that the execution is finished to show the read only mode
        if study_case_execution is not None and study_case_execution.execution_status == StudyCaseExecution.FINISHED:
            is_read_only_possible = True
            # show read_only_mode if needed and possible
        if is_read_only_possible:
            loaded_study_case = get_loaded_study_case_in_read_only_mode(study_case_identifier, study_access_right, study_case_execution)

    return loaded_study_case


def get_loaded_study_case_in_read_only_mode(study_id, study_access_right, study_execution):
    # Proceeding after rights verification
    # Get readonly file, in case of a restricted viewer get with no_data
    study_json = _get_study_in_read_only_mode(
        study_id, study_access_right == AccessRights.RESTRICTED_VIEWER)

    # check in read only file that the study status is DONE
    if study_json is not None:
        study_case_value = study_json.get("study_case")
        if study_case_value is not None:
            # set study access rights
            if study_access_right == AccessRights.MANAGER:
                study_case_value["is_manager"] = True
            elif study_access_right == AccessRights.CONTRIBUTOR:
                study_case_value["is_contributor"] = True
            elif study_access_right == AccessRights.COMMENTER:
                study_case_value["is_commenter"] = True
            else:
                study_case_value["is_restricted_viewer"] = True

            # Set execution status
            if study_execution is not None:
                study_case_value["execution_status"] = study_execution.execution_status
                study_case_value["last_memory_usage"] = study_execution.memory_usage
                study_case_value["last_cpu_usage"] = study_execution.cpu_usage

            # set creation status to DONE if not saved in read only mode
            study_case_value["creation_status"] = StudyCase.CREATION_DONE

            return study_json

    return None


def _get_study_in_read_only_mode(study_id, no_data):
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

            loaded_study_json["study_case"]['has_read_only_file'] = True

            # read dashboard and set it to the loaded study
            # (it takes less time to read it apart than to have the dashboard in the read only file)
            if len(loaded_study_json["post_processings"]) > 0:
                dashboard = study_manager.read_dashboard_in_json_file()
                loaded_study_json["dashboard"] = dashboard
            return loaded_study_json

        except Exception as error:
            app.logger.error(
                f"Study {study_id} readonly mode error while getting readonly file: {error}")
            return None
    else:
        return None


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


def check_pod_allocation_is_running(study_case_identifier):
    """
        :param study_case_identifier: id of the new study case
        :type study_case_identifier: integer
    """

    with app.app_context():
        is_running = False
        status = get_allocation_status_by_study_id(study_case_identifier)
        if status is not None and status == PodAllocation.RUNNING:
            is_running = True

        return is_running

def update_read_only_files_with_visualization():
    """"
    Load all study case with read only files, 
    build visualization diagrams and update diagrams in read only files
    """
    report = []
    with app.app_context():
        # get all study cases
        study_cases = StudyCase.query.filter(
            StudyCase.creation_status == StudyCase.CREATION_DONE).all()
        
        start = datetime.now()
        study_n2_diagrams_updated = []
        study_in_error_at_loading = []
        app.logger.info(f"Study cases to check: {len(study_cases)}\n")
        for study in study_cases:
            #check there is an existing read_only_mode file
            try:
                study_manager = StudyCaseManager(study.id)
                if study_manager.check_study_case_json_file_exists():
                    # get the read only file content
                    study_json = study_manager.read_loaded_study_case_in_json_file()
                    if study_json is not None:
                        # check there is no diagrams in the read_only
                        study_case_value = study_json.get(LoadedStudyCase.N2_DIAGRAM)
                        if (study_case_value is None or len(study_case_value) == 0 
                            or study_case_value.get(LoadedStudyCase.N2_DIAGRAM) is None or len(study_case_value.get(LoadedStudyCase.N2_DIAGRAM)) == 0 
                            or study_case_value.get(LoadedStudyCase.EXECUTION_SEQUENCE) is None or len(study_case_value.get(LoadedStudyCase.EXECUTION_SEQUENCE)) == 0
                            or study_case_value.get(LoadedStudyCase.INTERFACE_DIAGRAM) is None or len(study_case_value.get(LoadedStudyCase.INTERFACE_DIAGRAM)) == 0):
                            app.logger.info(f"Study case {study.id} has no diagrams\n")

                            # load the study from the pickle
                            study_manager.load_study_case_from_source()
                            app.logger.info(f"Study case {study.id} loaded\n")
                            # load n2 diagrams
                            loaded_study = LoadedStudyCase(study_manager, no_data=False, read_only=False, 
                                                           user_id=None, load_post_processings=False)
                            loaded_study.load_n2_diagrams(study_manager)
                            app.logger.info(f"Study case {study.id} N2 built\n")
                            # set n2 diagrams in the read only mode
                            if (study_case_value is None or len(study_case_value) == 0):
                                study_json[LoadedStudyCase.N2_DIAGRAM] = loaded_study.n2_diagram
                            else:
                                if study_case_value.get(LoadedStudyCase.N2_DIAGRAM) is None or len(study_case_value.get(LoadedStudyCase.N2_DIAGRAM)) == 0:
                                    study_json[LoadedStudyCase.N2_DIAGRAM][LoadedStudyCase.N2_DIAGRAM] = loaded_study.n2_diagram[LoadedStudyCase.N2_DIAGRAM]
                                    app.logger.info(f"Study case {study.id} update coupling diagram\n")
                                if study_case_value.get(LoadedStudyCase.EXECUTION_SEQUENCE) is None or len(study_case_value.get(LoadedStudyCase.EXECUTION_SEQUENCE)) == 0:
                                    study_json[LoadedStudyCase.N2_DIAGRAM][LoadedStudyCase.EXECUTION_SEQUENCE] = loaded_study.n2_diagram[LoadedStudyCase.EXECUTION_SEQUENCE]
                                    app.logger.info(f"Study case {study.id} update execution sequence diagram\n")
                                if study_case_value.get(LoadedStudyCase.INTERFACE_DIAGRAM) is None or len(study_case_value.get(LoadedStudyCase.INTERFACE_DIAGRAM)) == 0:
                                    study_json[LoadedStudyCase.N2_DIAGRAM][LoadedStudyCase.INTERFACE_DIAGRAM] = loaded_study.n2_diagram[LoadedStudyCase.INTERFACE_DIAGRAM]
                                    app.logger.info(f"Study case {study.id} update interface diagram\n")

                            # save the read only mode
                            study_file_path = Path(study_manager.dump_directory).joinpath(StudyCaseManager.LOADED_STUDY_FILE_NAME)
                            write_object_in_json_file(study_json, study_file_path)
                            app.logger.info(f"Study case {study.id} read only file written\n")
                            study_n2_diagrams_updated.append(study.id)
            except Exception as exp:
                # the study cannot be reloaded
                app.logger.error(f"error while updating read only mode of study {study.id}: {str(exp)}")
                study_in_error_at_loading.append(study.id)
                pass
    
    app.logger.info(f"Total Study cases checked: {len(study_cases)}\n")
    app.logger.info(f"total updated diagrams: {len(study_n2_diagrams_updated)}")
    app.logger.info(f"updated diagrams of studies: {study_n2_diagrams_updated}")
    app.logger.info(f"total studies in error at loading: {len(study_in_error_at_loading)}")
    app.logger.info(f"studies in error at loading: {study_in_error_at_loading}")
    app.logger.info(f"total time: {datetime.now()-start}")
