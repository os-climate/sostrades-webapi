'''
Copyright 2022 Airbus SAS

Modifications on 2024/04/05 Copyright 2024 Capgemini
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
Reference generation subprocess launch
"""


class ReferenceGenerationSubprocess:
    """
    Class that allow to launch reference generation process as
    system subprocess
    """

    def __init__(self, reference_identifier):
        """
        Class constructor

        :params: reference_identifier, database identifier of the reference to generate
        :type: integer
        """
        self.__reference_identifier = reference_identifier

    def run(self):
        """
        Launch the process using subprocess.Popen
        """
        path = join(dirname(sos_trades_api.__file__),
                    "..", "server_scripts", "calculation", "launch_calculation.py")
        process = subprocess.Popen(
            f'python "{path}" --generate {self.__reference_identifier}', shell=True, stdin=subprocess.PIPE)

        return process.pid
