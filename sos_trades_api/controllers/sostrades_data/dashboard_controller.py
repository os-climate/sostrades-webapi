from pathlib import Path

from sos_trades_api.server.base_server import app
from sos_trades_api.tools.file_tools import write_object_in_json_file
from sos_trades_api.tools.loading.study_case_manager import StudyCaseManager


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
            return {}
    else:
        return {}


def save_study_dashboard_in_file(dashboard_data):
    """
    save the dashboard data into a json file and check if a json file exists already
         if true, replace the existing json file
         if false, create a new json file
     :param: dashboard_data, data of the dashboard to save
     :type: Object({study_case_id, items})
    """
    study_manager = StudyCaseManager(dashboard_data['study_case_id'])
    dashboard_file_path = Path(study_manager.dump_directory).joinpath(study_manager.DASHBOARD_FILE_NAME)
    write_object_in_json_file(dashboard_data, dashboard_file_path)
    return