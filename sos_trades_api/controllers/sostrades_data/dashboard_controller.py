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
    dashboard_file_path = study_manager.get_dashboard_file_path()
    write_object_in_json_file(dashboard_data, dashboard_file_path)
    return