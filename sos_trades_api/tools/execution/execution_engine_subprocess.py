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
Execution engine threadns
"""
import subprocess
from os.path import join, dirname
import sos_trades_api


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
                    '..', 'server_scripts', 'calculation', 'launch_calculation.py')

        with open(self.__log_file_path, 'wb') as log_file:

            process = subprocess.Popen(
                #f'python "{path}" --execute {self.__study_case_execution_id}',
                f'memray run --trace-python-allocators "{path}" --execute {self.__study_case_execution_id}',
                shell=True, stdout=log_file,stderr=log_file)

        return process.pid
