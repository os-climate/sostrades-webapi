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
from shutil import rmtree

from sos_trades_api.models.database_models import (
    AccessRights,
    Group,
    GroupAccessUser,
    StudyCase,
    User,
)
from sos_trades_api.server.base_server import app, db
from sos_trades_api.tools.loading.study_case_manager import StudyCaseManager
from sos_trades_api.tools.right_management.functional.tools_access_right import (
    ResourceAccess,
)


class GroupError(Exception):
    """Base Group Exception"""

    def __init__(self, msg=None):
        Exception.__init__(self, msg)

    def __str__(self):
        return self.__class__.__name__ + "(" + Exception.__str__(self) + ")"


class InvalidGroupName(GroupError):
    """Invalid Group Name"""


class InvalidGroup(GroupError):
    """Invalid Group"""


def get_all_groups():
    """Retrieve all groups"""
    groups_query = Group.query.all()

    return groups_query


def get_group_list(user_id):
    """
    get the group list of a user
    :params: user_id, id of the user
    :type: integer
    """
    res_access = ResourceAccess(user_id)

    return sorted(res_access.user_loaded_groups_list, key=lambda gr: gr.group.name.lower())


def create_group(user_id, name, description, confidential):
    """
    create a group
    :params: user_id, id of the user
    :type: integer
    :params: name, name of the group
    :type: string
    :params: description, description of the group
    :type: string
    :params: confidential, indicate if the group is private
    :type: boolean
    """
    group_query = Group.query.all()

    for grp in group_query:
        if grp.name == name:
            raise InvalidGroupName(
                f"The following group name : {name}, already exists in database")
        else:
            db.session.expunge(grp)

    try:

        group = Group()
        group.name = name
        group.description = description
        group.confidential = confidential

        # Creation of the group
        db.session.add(group)
        db.session.commit()

        # Give Owner right to group creator
        owner_right = AccessRights.query.filter(
            AccessRights.access_right == AccessRights.OWNER).first()

        if owner_right is not None:
            # Add owner to group members
            group_access_user = GroupAccessUser()
            group_access_user.group_id = group.id
            group_access_user.user_id = user_id
            group_access_user.right_id = owner_right.id
            db.session.add(group_access_user)
            db.session.commit()

            return group

        raise InvalidGroup(
            "Error creating group : Owner right not found in database.")
    except Exception as error:
        raise InvalidGroup(
            f"Group creation raise the following error : {error}")


def delete_group(group_id):
    """
    Delete a group from database

    :params: group_id, group to delete primary key
    :type: integer
    """
    # Get db group object
    query_group = Group.query.filter(Group.id == group_id).first()

    if query_group is not None:

        # Retrieve all users who have as default group, the group that will be deleted and set their default group at None
        users_by_default_group_id = db.session.query(User).filter(
            User.default_group_id == group_id).all()
        if users_by_default_group_id is not None:
            for user in users_by_default_group_id:
                user.default_group_id = None

        # retrieve studies in this group
        studycases_to_delete = StudyCase.query.filter(StudyCase.group_id == group_id).all()
        # Remove group from db
        db.session.delete(query_group)

        # update the group_members_ids of group_access_group after the removal
        # of the group
        ResourceAccess.update_group_members_ids(group_id)
        db.session.commit()

        # delete group folder with all study case in it
        folder = StudyCaseManager.get_root_study_data_folder(group_id)
        rmtree(folder, ignore_errors=True)

        return f"The group (identifier {group_id}) has been deleted in the database"

    raise InvalidGroup(
        f"The following group with group_id : {group_id}, cannot be found in database")


def rename_applicative_group(new_group_name):
    """
    rename a group from database

    :params: old_group_name, current name of the group
    :type: string
    :params: new_group_name, new name of the group
    :type: string
    """
    # Get db group object
    query_group = Group.query.filter(Group.is_default_applicative_group).first()
    query_new_group = Group.query.filter(Group.name == new_group_name).first()

    if query_new_group is not None:
        raise InvalidGroup(
            f"The following group with group name : {new_group_name}, already exists in database")

    if query_group is not None and query_new_group is None:
        query_group.name = new_group_name
        db.session.commit()
        print(f"The group has been renamed into {new_group_name}")


def edit_group(group_id, name, description,user_id):
    """
    update a group from database

    :params name: New name of the group
    :type: string
    :params description: New description of the group
    :type: string
    :params user_id: User that update this link
    """
    # Get db group object
    group = Group.query.filter(Group.id == group_id).first()

    if group is not None:

        try:
            group.name = name
            group.description = description
            db.session.commit()

            app.logger.info(
                f'The user id: "{user_id}"has been successfully updated the group (id: {group_id}){group.name}"',
            )

        except Exception as ex:
            db.session.rollback()
            raise ex

    else:
        raise InvalidGroup("Group cannot be found in the database")

    return group


def add_group_access_from_keycloak(user_id, group):
        if group is not None:
            # Add member right
            member_right = AccessRights.query.filter(
                AccessRights.access_right == AccessRights.MEMBER).first()
            group_access = GroupAccessUser.query.filter(GroupAccessUser.group_id == group.id,
                                                        GroupAccessUser.user_id == user_id).first()
            if member_right is not None and group_access is None:
                group_access_user = GroupAccessUser()
                group_access_user.group_id = group.id
                group_access_user.user_id = user_id
                group_access_user.right_id = member_right.id
                db.session.add(group_access_user)
                db.session.commit()

