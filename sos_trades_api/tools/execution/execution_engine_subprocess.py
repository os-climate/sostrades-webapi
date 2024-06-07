'''
Copyright 2022 Airbus SAS
Modifications on 2024/06/07 Copyright 2024 Capgemini
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
import subprocess
from os.path import dirname, join

import sos_trades_api

"""
Execution engine subprocess
"""

class ExecutionEngineSubprocess:

    def __init__(self, study_case_execution_id, log_file_path):
        """

        :param study_case_execution_id: study case execution to run
        :param log_file_path: file to redirect stdout and stderr
        """
        self.__study_case_execution_id = study_case_execution_id
        self.__log_file_path = log_file_path

    def run(self):
        path = join(dirname(sos_trades_api.__file__),
                    "..", "server_scripts", "calculation", "launch_calculation.py")

        with open(self.__log_file_path, "wb") as log_file:

            process = subprocess.Popen(
                f'python "{path}" --execute {self.__study_case_execution_id}',
                shell=True, stdout=log_file,stderr=log_file)

        return process.pid
