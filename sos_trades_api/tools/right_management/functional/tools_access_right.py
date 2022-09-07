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
from sos_trades_api.models.database_models import Group, GroupAccessGroup, GroupAccessUser, AccessRights
from sos_trades_api.server.base_server import db
from sos_trades_api.models.loaded_group import LoadedGroup


class ResourceAccess:
    """ Class containing the access right of a specific ressource of SoSTrades.
    """

    def __init__(self, user_id):
        """Constructor
        """
        self.user_id = user_id
        self.user_groups_list = []
        self.user_loaded_groups_list = []
        self.set_user_full_group_list_with_rights()

    def set_user_full_group_list_with_rights(self):
        # Retrieving groups authorised by user_id
        user_groups_list = db.session.query(Group, AccessRights) \
            .filter(Group.id == GroupAccessUser.group_id) \
            .filter(GroupAccessUser.user_id == self.user_id) \
            .filter(AccessRights.id == GroupAccessUser.right_id).all()

        for ug in user_groups_list:
            # Adding group to group list
            self.user_groups_list.append(ug[0])
            # Adding group to loaded group list
            new_loaded_group = LoadedGroup(ug[0])
            if ug[1].access_right == AccessRights.OWNER:
                new_loaded_group.is_owner = True
            elif ug[1].access_right == AccessRights.MANAGER:
                new_loaded_group.is_manager = True
            elif ug[1].access_right == AccessRights.MEMBER:
                new_loaded_group.is_member = True
            self.user_loaded_groups_list.append(new_loaded_group)

        # store user_group_list_ids
        user_group_ids = [g.id for g in self.user_groups_list]

        # retrieve all  subgroups of each group user access authorised with
        # access rights
        for ugi in user_group_ids:
            group_groups = db.session.query(Group, AccessRights) \
                .filter(Group.id == GroupAccessGroup.group_id) \
                .filter(GroupAccessGroup.group_members_ids.like(f'%.{ugi}.%')) \
                .filter(AccessRights.id == GroupAccessGroup.right_id).all()

            for ggl in group_groups:
                if len(list(filter(lambda ugg: ugg.id == ggl[0].id, self.user_groups_list))) > 0:
                    # Updating loaded group on already existing group
                    updated_loaded_group = list(
                        filter(lambda ugg: ugg.group.id == ggl[0].id, self.user_loaded_groups_list))[0]
                    if ggl[1].access_right == AccessRights.OWNER:
                        updated_loaded_group.is_owner = True
                    elif ggl[1].access_right == AccessRights.MANAGER:
                        updated_loaded_group.is_manager = True
                    elif ggl[1].access_right == AccessRights.MEMBER:
                        updated_loaded_group.is_member = True
                else:
                    # Adding group to group list
                    self.user_groups_list.append(ggl[0])
                    # Adding group to loaded group list
                    new_loaded_group = LoadedGroup(ggl[0])
                    if ggl[1].access_right == AccessRights.OWNER:
                        new_loaded_group.is_owner = True
                    elif ggl[1].access_right == AccessRights.MANAGER:
                        new_loaded_group.is_manager = True
                    elif ggl[1].access_right == AccessRights.MEMBER:
                        new_loaded_group.is_member = True
                    self.user_loaded_groups_list.append(new_loaded_group)

        # Sorting lists by group name
        self.user_groups_list = sorted(
            self.user_groups_list, key=lambda gr: gr.name.lower())
        self.user_loaded_groups_list = sorted(
            self.user_loaded_groups_list, key=lambda gl: gl.group.name.lower())

    @staticmethod
    def generate_group_members_ids(group_member_id):
        # initialise a set with the group member id
        group_members_ids = {group_member_id}
        ResourceAccess.get_children_group_id_recurse(
            group_member_id, group_members_ids)

        # create a string of ids from the set
        str_group_members_ids = f'.'
        for sub_id in group_members_ids:
            str_group_members_ids = f'{str_group_members_ids}{sub_id}.'

        return str_group_members_ids

    @staticmethod
    def get_children_group_id_recurse(group_id, children_id_set):
        children_group_access_groups = GroupAccessGroup.query.filter(
            GroupAccessGroup.group_id == group_id).all()
        for children_group in children_group_access_groups:
            # this test is to avoid infinite loops
            if children_group.group_member_id not in children_id_set:
                children_id_set.add(children_group.group_member_id)
                ResourceAccess.get_children_group_id_recurse(
                    children_group.group_member_id, children_id_set)

    @staticmethod
    def update_group_members_ids(group_id_to_look_for, filtered_id=None):
        # retrieve all group_access_group containing the group_id_to_look_for
        # that has been created or deleted
        group_access_group_to_update = GroupAccessGroup.query.filter(GroupAccessGroup.group_members_ids.like(
            f'%.{group_id_to_look_for}.%'), GroupAccessGroup.id != filtered_id).all()
        if len(group_access_group_to_update) > 0:
            for group_access_group in group_access_group_to_update:
                # update the group_members_ids field
                str_group_members_ids = ResourceAccess.generate_group_members_ids(
                    group_access_group.group_member_id)
                group_access_group.group_members_ids = str_group_members_ids
