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
Class that represent all the study case notifications with changes
"""


class StudyNotification:

    def __init__(self, id, created, author, type, message, changes):
        self.id = id
        self.created = created
        self.author = author
        self.type = type
        self.message = message
        self.changes = changes

    def serialize(self):
        """
        json serializer for dto purpose
        """
        return {
            "id": self.id,
            "created": self.created,
            "author": self.author,
            "type": self.type,
            "message": self.message,
            "changes": self.changes,
        }
