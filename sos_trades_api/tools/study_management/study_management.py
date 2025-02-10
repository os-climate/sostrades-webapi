from pathlib import Path

from sos_trades_api.controllers.error_classes import InvalidFile, StudyCaseError
from sos_trades_api.models.database_models import (
    AccessRights,
    PodAllocation,
    StudyCase,
    StudyCaseExecution,
)
from sos_trades_api.models.loaded_study_case import LoadStatus
from sos_trades_api.models.study_case_dto import StudyCaseDto
from sos_trades_api.server.base_server import app, study_case_cache
from sos_trades_api.tools.allocation_management.allocation_management import (
    get_allocation_status_by_study_id,
)
from sos_trades_api.tools.loading.study_case_manager import StudyCaseManager


def check_read_only_file_exist(user_study: StudyCaseDto):
    file_exist = False
    # Create path to retrieve to the file loaded_study_case.json
    sostrades_data_path = Path(app.config["SOS_TRADES_DATA"], "study_case")
    group_path = sostrades_data_path / str(user_study.group_id)
    study_path = group_path / str(user_study.id)
    study_file = study_path / "loaded_study_case.json"

    # Check if paths and file exist
    if group_path.exists():
        if study_path.exists():
            if study_file.is_file():
                if user_study.execution_status == StudyCaseExecution.FINISHED:
                    file_exist = True
                    return file_exist
                else:
                    # If StudyCaseExecution is not FINISHED, the loaded_study_case.json does not exist anymore
                    study_file.unlink()
                    app.logger.info(f"loaded_study_case.json for {user_study.id} has been deleted because his status is not Finished")
        else:
            app.logger.error(f"The folder of study_id {user_study.id} in the group {user_study.group_id} is not existing")
    else:
        app.logger.error(f"The folder of group_id {user_study.group_id} is not existing")

    return file_exist


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
            loaded_study_case = get_loaded_study_case_in_read_only_mode(study_case_identifier, study_access_right)
    return loaded_study_case


def get_loaded_study_case_in_read_only_mode(study_id, study_access_right):
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
                study_json["study_case"]["is_manager"] = True
            elif study_access_right == AccessRights.CONTRIBUTOR:
                study_json["study_case"]["is_contributor"] = True
            elif study_access_right == AccessRights.COMMENTER:
                study_json["study_case"]["is_commenter"] = True
            else:
                study_json["study_case"]["is_restricted_viewer"] = True

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

        return is_running
