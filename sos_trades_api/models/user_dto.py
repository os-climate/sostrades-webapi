'''
Copyright 2024 Capgemini

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
Class that represent a study case data transfert object with group information
"""
from sos_trades_api.models.database_models import User


class UserDto:

    def __init__(self, user_id):
        """ Initialize DTO using a study case instance

        :params: user_id : user identifier
        :type: integer
        """

        self.id = user_id
        self.username = ""
        self.firstname = ""
        self.lastname = ""
        self.department = ""
        self.user_profile_id = ""

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'id': self.id,
            'username': self.username,
            'firstname': self.firstname,
            'lastname': self.lastname,
            'department': self.department,
            'userprofile': self.user_profile_id
        }
