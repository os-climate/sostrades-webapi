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
Class that represent a state of an executed study case
"""


class LoadedStudyCaseExecutionStatus:

    def __init__(self, study_case_id, study_case_execution, study_case_execution_status,
                 study_case_execution_cpu, study_case_execution_memory):

        self.study_case_id = study_case_id
        self.study_case_execution = study_case_execution
        self.study_case_execution_status = study_case_execution_status
        self.study_case_execution_cpu = study_case_execution_cpu
        self.study_case_execution_memory = study_case_execution_memory

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'study_case_id': self.study_case_id,
            'disciplines_status': self.study_case_execution,
            'study_case_execution_status': self.study_case_execution_status,
            'study_case_execution_cpu': self.study_case_execution_cpu,
            'study_case_execution_memory': self.study_case_execution_memory
        }
