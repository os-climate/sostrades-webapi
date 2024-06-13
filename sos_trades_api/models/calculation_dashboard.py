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
"""
mode: python; py-indent-offset: 4; tab-width: 4; coding: utf-8
Class that represent data needed for calculation dashboard
"""


class CalculationDashboard:

    def __init__(self, study_case_id, name, study_case_execution_id, creation_date, repository, process,
                 repository_display_name, process_display_name, username, execution_status):
        self.study_case_id = study_case_id
        self.name = name
        self.study_case_execution_id = study_case_execution_id
        self.repository = repository
        self.process = process
        self.process_display_name = process_display_name
        self.repository_display_name = repository_display_name
        self.creation_date = creation_date
        self.username = username
        self.execution_status = execution_status

    def serialize(self):
        """
        json serializer for dto purpose
        """
        return {
            "study_case_id": self.study_case_id,
            "name": self.name,
            "study_case_execution_id": self.study_case_execution_id,
            "repository": self.repository,
            "process": self.process,
            "repository_display_name": self.repository_display_name,
            "process_display_name": self.process_display_name,
            "creation_date": self.creation_date,
            "username": self.username,
            "execution_status": self.execution_status,
        }
