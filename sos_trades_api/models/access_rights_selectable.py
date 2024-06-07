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
from sos_trades_api.models.database_models import AccessRights

"""
Class that represent access right model + selectable information
"""

class AccessRightsSelectable:
    # old StudyGroup
    def __init__(self, access_right):

        if access_right is not None:
            self.id = access_right.id
            self.access_right = access_right.access_right
            self.description = access_right.description
            self.selectable = True

            if self.access_right == AccessRights.OWNER:
                self.selectable = False

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'id': self.id,
            'access_right': self.access_right,
            'description': self.description,
            'selectable': self.selectable
        }
