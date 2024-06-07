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

from sos_trades_api.tools.right_management.access_right import get_applicative_module

"""
Class that represent a user with his profile name
"""

class UserApplicationRight:

    def __init__(self, user):
        self.user = user  # User class
        self.modules = get_applicative_module(self.user.user_profile_id)

    def __repr__(self):
        """
        Overload of the class representation
        """
        return f"{self.user.id} | {self.user.user_profile_id} | {self.modules}"

    def serialize(self):
        """
        json serializer for dto purpose
        """
        return {
            "user": self.user,
            "modules": self.modules,
        }
