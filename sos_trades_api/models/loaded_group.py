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
Class that represent the link between the study and his group
"""


class LoadedGroup:
    # old StudyGroup
    def __init__(self, group):
        self.group = group
        self.is_owner = False
        self.is_manager = False
        self.is_member = False

    def serialize(self):
        """
        json serializer for dto purpose
        """
        return {
            "group": self.group,
            "is_owner": self.is_owner,
            "is_manager": self.is_manager,
            "is_member": self.is_member,
        }
