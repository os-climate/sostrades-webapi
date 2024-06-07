'''
Copyright 2022 Airbus SAS
Modifications on 2023/08/03-2023/11/03 Copyright 2023 Capgemini

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
from sos_trades_api.models.database_models import (
    AccessRights,
    Group,
    GroupAccessGroup,
    GroupAccessUser,
)
from sos_trades_api.models.loaded_group import LoadedGroup
from sos_trades_api.server.base_server import db


class ResourceAccess:
    """Class containing the access right of a specific resource of SoSTrades."""

    def __init__(self, user_id):
        """
        Constructor
        :param user_id: user identifier to manage
        :type user_id: int
        """

        self.user_id = user_id
        self.__reset()
        self.set_user_full_group_list_with_rights()

    def __reset(self):
        """
        Re set some members variables
        """
        self._user_groups_list = {}
        self._user_loaded_groups_list = {}

    @property
    def user_loaded_groups_list(self):
        """
        Return the list of user available group
        :return: sos_trades_api.models.database_models.LoadedGroup[]
        """
        return list(self._user_loaded_groups_list.values())

    def set_user_full_group_list_with_rights(self):
        """
        Manage to load user available groups
        """
        self.__reset()

        # Retrieving groups authorised by user_id
        user_groups_list = (
            db.session.query(Group, AccessRights)
            .filter(Group.id == GroupAccessUser.group_id)
            .filter(GroupAccessUser.user_id == self.user_id)
            .filter(AccessRights.id == GroupAccessUser.right_id)
            .all()
        )

        for ug in user_groups_list:

            current_user_group = ug[0]
            current_access_rights = ug[1]

            # Adding group to group list
            if current_user_group.id not in self._user_groups_list:
                self._user_groups_list[current_user_group.id] = current_user_group

                # Adding group to loaded group list
                new_loaded_group = LoadedGroup(current_user_group)
                if current_access_rights.access_right == AccessRights.OWNER:
                    new_loaded_group.is_owner = True
                elif current_access_rights.access_right == AccessRights.MANAGER:
                    new_loaded_group.is_manager = True
                elif current_access_rights.access_right == AccessRights.MEMBER:
                    new_loaded_group.is_member = True

                self._user_loaded_groups_list[
                    new_loaded_group.group.id
                ] = new_loaded_group

        # retrieve all  subgroups of each group user access authorised with
        # access rights
        init_user_groups_list = list(self._user_groups_list.keys())
        for ugi in init_user_groups_list:
            group_groups = (
                db.session.query(Group, AccessRights)
                .filter(Group.id == GroupAccessGroup.group_id)
                .filter(GroupAccessGroup.group_members_ids.like(f'%.{ugi}.%'))
                .filter(AccessRights.id == GroupAccessGroup.right_id)
                .all()
            )

            for ggl in group_groups:
                current_group_of_group = ggl[0]
                current_access_rights = ggl[1]
                loaded_group_to_manage = None

                if current_group_of_group.id in self._user_groups_list:
                    # Updating loaded group on already existing group
                    loaded_group_to_manage = self._user_loaded_groups_list[
                        current_group_of_group.id
                    ]
                else:
                    # Adding group to group list
                    self._user_groups_list[
                        current_group_of_group.id
                    ] = current_group_of_group

                    # Adding group to loaded group list
                    loaded_group_to_manage = LoadedGroup(current_group_of_group)
                    self._user_loaded_groups_list[
                        loaded_group_to_manage.group.id
                    ] = loaded_group_to_manage

                if current_access_rights.access_right == AccessRights.OWNER:
                    loaded_group_to_manage.is_owner = True
                elif current_access_rights.access_right == AccessRights.MANAGER:
                    loaded_group_to_manage.is_manager = True
                elif current_access_rights.access_right == AccessRights.MEMBER:
                    loaded_group_to_manage.is_member = True

    @staticmethod
    def generate_group_members_ids(group_member_id):
        # initialise a set with the group member id
        group_members_ids = {group_member_id}
        ResourceAccess.get_children_group_id_recurse(group_member_id, group_members_ids)

        # create a string of ids from the set
        str_group_members_ids = '.'
        for sub_id in group_members_ids:
            str_group_members_ids = f'{str_group_members_ids}{sub_id}.'

        return str_group_members_ids

    @staticmethod
    def get_children_group_id_recurse(group_id, children_id_set):
        children_group_access_groups = GroupAccessGroup.query.filter(
            GroupAccessGroup.group_id == group_id
        ).all()
        for children_group in children_group_access_groups:
            # this test is to avoid infinite loops
            if children_group.group_member_id not in children_id_set:
                children_id_set.add(children_group.group_member_id)
                ResourceAccess.get_children_group_id_recurse(
                    children_group.group_member_id, children_id_set
                )

    @staticmethod
    def update_group_members_ids(group_id_to_look_for, filtered_id=None):
        # retrieve all group_access_group containing the group_id_to_look_for
        # that has been created or deleted
        group_access_group_to_update = GroupAccessGroup.query.filter(
            GroupAccessGroup.group_members_ids.like(f'%.{group_id_to_look_for}.%'),
            GroupAccessGroup.id != filtered_id,
        ).all()
        if len(group_access_group_to_update) > 0:
            for group_access_group in group_access_group_to_update:
                # update the group_members_ids field
                str_group_members_ids = ResourceAccess.generate_group_members_ids(
                    group_access_group.group_member_id
                )
                group_access_group.group_members_ids = str_group_members_ids
