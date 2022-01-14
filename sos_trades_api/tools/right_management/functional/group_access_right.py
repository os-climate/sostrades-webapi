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
methods to define access rights for a group
"""

from sos_trades_api.models.database_models import Group, User,\
    AccessRights, GroupAccessGroup, GroupAccessUser
from sos_trades_api.tools.right_management.functional.tools_access_right import ResourceAccess
from sos_trades_api.base_server import app
from sos_trades_core.tools.sos_logger import SoSLogging


class GroupAccess(ResourceAccess):

    """ Class containing the access right of a group of SoSTrades.
    """

    def __init__(self, user_id):
        """Constructor
        """
        ResourceAccess.__init__(self, user_id)

        # Initialize execution logger
        self.__logger = SoSLogging(
            'SoS.AccessRight', level=SoSLogging.WARNING).logger

    def check_user_right_for_group(self, right_type, group_id=None):
        """ Methods that check that the given user right to have a specific right for a specific process
        """
        has_access = False
        if group_id is not None:

            with app.app_context():
                # Search in complete loaded group list authorised for user
                grp_right = list(filter(lambda ugg: ugg.group.id == group_id, self.user_loaded_groups_list))

                if len(grp_right) > 0:
                    if right_type == AccessRights.OWNER:
                        if grp_right[0].is_owner:
                            has_access = True

                    if right_type == AccessRights.MANAGER:
                        if grp_right[0].is_manager or grp_right[0].is_owner:
                            has_access = True

                    elif right_type == AccessRights.MEMBER:
                        if grp_right[0].is_member or grp_right[0].is_manager or grp_right[0].is_owner:
                            has_access = True

        return has_access
