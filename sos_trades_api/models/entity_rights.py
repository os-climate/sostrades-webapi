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
Class that represent entities : User or Group with associated rights (relative to a Resource)
"""
import abc
from sos_trades_api.models.access_rights_selectable import AccessRightsSelectable
from sos_trades_api.models.database_models import StudyCaseAccessGroup,\
    StudyCaseAccessUser, Group, User, ProcessAccessGroup, ProcessAccessUser,\
    AccessRights, GroupAccessGroup, GroupAccessUser
from sqlalchemy import or_
from sos_trades_api.tools.right_management.functional.tools_access_right import ResourceAccess


class EntityRightsError(Exception):
    """Base EntityRights Exception"""

    def __init__(self, msg=None):
        Exception.__init__(self, msg)


class EntityType:
    GROUP = 'group'
    USER = 'user'


class ResourceType:
    PROCESS = 'process'
    GROUP = 'group'
    STUDYCASE = 'study_case'
    SOSDISCIPLINE = 'sos_discipline'


class EntityRight:

    def __init__(self):
        self.id = -1
        self.entity_type = ''
        self.entity_object = None
        self.selected_right = ''
        self.locked = False

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'id': self.id,
            'entity_type': self.entity_type,
            'entity_object': self.entity_object,
            'selected_right': self.selected_right,
            'locked': self.locked
        }

    def deserialize(self, json_dict):
        self.id = json_dict['id']
        self.entity_type = json_dict['entityType']

        new_obj = None
        if self.entity_type == EntityType.GROUP:
            new_obj = Group()
            new_obj.id = json_dict['entityObject']['id']
        elif self.entity_type == EntityType.USER:
            new_obj = User()
            new_obj.id = json_dict['entityObject']['id']

        self.entity_object = new_obj
        self.selected_right = json_dict['selectedRight']


class EntityRights:

    def __init__(self):

        self.resource_id = None
        self.resource_type = ''
        self.available_rights = []
        self.entities_rights = []

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'resource_id': self.resource_id,
            'resource_type': self.resource_type,
            'available_rights': self.available_rights,
            'entities_rights': self.entities_rights,
        }

    def deserialize(self, json_dict):

        self.resource_id = json_dict['resourceId']
        self.resource_type = json_dict['resourceType']

        if len(json_dict['entitiesRights']) > 0:
            for ent in json_dict['entitiesRights']:
                new_entity = EntityRight()
                new_entity.deserialize(ent)
                self.entities_rights.append(new_entity)


def apply_entity_rights_changes(db_session, json_data, user_id):

    new_entity = EntityRights()
    new_entity.deserialize(json_data)

    # PROCESS RESOURCE
    if new_entity.resource_type == ResourceType.PROCESS:
        process_entity = ProcessEntityRights(None, new_entity)
        process_entity.apply_db_changes(db_session, user_id)

    # GROUP RESOURCE
    elif new_entity.resource_type == ResourceType.GROUP:
        group_entity = GroupEntityRights(None, new_entity)
        group_entity.apply_db_changes(db_session, user_id)

    # STUDYCASE RESOURCE
    elif new_entity.resource_type == ResourceType.STUDYCASE:
        study_entity = StudyCaseEntityRights(None, new_entity)
        study_entity.apply_db_changes(db_session, user_id)

    # SOSDISCIPLINE RESOURCE
    elif new_entity.resource_type == ResourceType.SOSDISCIPLINE:
        pass


def check_not_current_user(user_id_changed, current_user_id):
    if user_id_changed == current_user_id:
        raise EntityRightsError(
            'You are not allowed to modify your own rights.')


class ProcessEntityRights():

    def __init__(self, process_id=None, entity_rights=None):
        if entity_rights is None:
            self.entity = EntityRights()
            self.entity.resource_type = ResourceType.PROCESS
            self.entity.resource_id = process_id
        else:
            self.entity = entity_rights

        # Retrieve manager and contributor db object
        manager_right = AccessRights.query.filter(
            AccessRights.access_right == AccessRights.MANAGER).first()
        contributor_right = AccessRights.query.filter(
            AccessRights.access_right == AccessRights.CONTRIBUTOR).first()

        self.entity.available_rights = []

        if manager_right is not None and contributor_right is not None:
            self.entity.available_rights.append(
                AccessRightsSelectable(manager_right))
            self.entity.available_rights.append(
                AccessRightsSelectable(contributor_right))

    def add_access_db_object(self, access_db_object, user_id):

        entity_object = None
        entity_type = ''

        if isinstance(access_db_object, ProcessAccessGroup):

            entity_type = EntityType.GROUP
            entity_object = Group.query.filter_by(
                id=access_db_object.group_id).first()

            if entity_object is None:
                raise EntityRightsError(
                    f'Group object id {access_db_object.group_id} not found.')

        elif isinstance(access_db_object, ProcessAccessUser):

            entity_type = EntityType.USER
            entity_object = User.query.filter_by(
                id=access_db_object.user_id).first()

            if entity_object is None:
                raise EntityRightsError(
                    f'User object id {access_db_object.user_id} not found.')

        else:
            raise EntityRightsError(
                f'ProcessEntityRights setup error, bad access_db_object.\n ProcessAccessGroup or ProcessAccessUser '
                f'intended but {type(access_db_object)} given')

        new_entity_right = EntityRight()
        new_entity_right.entity_type = entity_type
        new_entity_right.id = access_db_object.id
        new_entity_right.entity_object = entity_object
        new_entity_right.selected_right = access_db_object.right_id

        if isinstance(access_db_object, ProcessAccessUser):
            if new_entity_right.entity_object.id == user_id:
                new_entity_right.locked = True

        self.entity.entities_rights.append(new_entity_right)

    def apply_db_changes(self, db_session, user_id):

        for ent_changes in self.entity.entities_rights:

            if ent_changes.entity_type == EntityType.GROUP:
                self.change_process_group(db_session, ent_changes)

            elif ent_changes.entity_type == EntityType.USER:
                self.change_process_user(db_session, ent_changes, user_id)

    def change_process_group(self, db_session, entity_change):
        if entity_change.id == -1:  # New object to create
            new_object = ProcessAccessGroup()
            new_object.group_id = entity_change.entity_object.id
            new_object.process_id = self.entity.resource_id
            new_object.right_id = entity_change.selected_right
            new_object.source = ProcessAccessGroup.SOURCE_USER
            db_session.add(new_object)

        else:  # Update or remove object from database
            if entity_change.selected_right is not None:  # Update object
                update_object = ProcessAccessGroup.query.filter(
                    ProcessAccessGroup.id == entity_change.id).first()

                if update_object is not None:
                    update_object.right_id = entity_change.selected_right
                    #set source to USER so that it is set as a user action
                    update_object.source = ProcessAccessGroup.SOURCE_USER

            else:  # Remove object
                self.check_not_last_process_manager(entity_change)
                delete_object = ProcessAccessGroup.query.filter(
                    ProcessAccessGroup.id == entity_change.id).first()

                if delete_object is not None:
                    db_session.delete(delete_object)

    def change_process_user(self, db_session, entity_change, user_id):
        if entity_change.id == -1:  # New object to create
            new_object = ProcessAccessUser()
            new_object.user_id = entity_change.entity_object.id
            new_object.process_id = self.entity.resource_id
            new_object.right_id = entity_change.selected_right
            new_object.source = ProcessAccessUser.SOURCE_USER
            db_session.add(new_object)

        else:  # Update or remove object from database
            if entity_change.selected_right is not None:  # Update object
                check_not_current_user(entity_change.entity_object.id, user_id)
                update_object = ProcessAccessUser.query.filter(
                    ProcessAccessUser.id == entity_change.id).first()

                if update_object is not None:
                    update_object.right_id = entity_change.selected_right
                    #set source to USER so that it is set as a user action
                    update_object.source = ProcessAccessUser.SOURCE_USER
                    
            else:  # Remove object
                self.check_not_last_process_manager(entity_change)
                delete_object = ProcessAccessUser.query.filter(
                    ProcessAccessUser.id == entity_change.id).first()

                if delete_object is not None:
                    db_session.delete(delete_object)

    def check_not_last_process_manager(self, entity_change):

        # Get manager right id
        manager_right = AccessRights.query.filter(
            AccessRights.access_right == AccessRights.MANAGER).first()

        if manager_right is not None:

            # Check entity id right is manager
            if entity_change.entity_type == EntityType.GROUP:
                entity_tested = ProcessAccessGroup.query.filter(
                    ProcessAccessGroup.id == entity_change.id).first()

                if entity_tested is not None:
                    if entity_tested.right_id == manager_right.id:
                        if self.count_manager_for_process() <= 1:
                            raise EntityRightsError(
                                'You cannot delete the last manager of a process')

            elif entity_change.entity_type == EntityType.USER:
                entity_tested = ProcessAccessUser.query.filter(
                    ProcessAccessUser.id == entity_change.id).first()

                if entity_tested is not None:
                    if entity_tested.right_id == manager_right.id:
                        if self.count_manager_for_process() <= 1:
                            raise EntityRightsError(
                                'You cannot delete the last manager of a process')

    def count_manager_for_process(self):
        managers_users = ProcessAccessUser.query.join(AccessRights).filter(
            ProcessAccessUser.process_id == self.entity.resource_id).filter(
            AccessRights.access_right == AccessRights.MANAGER).all()

        managers_groups = ProcessAccessGroup.query.join(AccessRights).filter(
            ProcessAccessGroup.process_id == self.entity.resource_id).filter(
            AccessRights.access_right == AccessRights.MANAGER).all()

        return len(managers_users) + len(managers_groups)

    def serialize(self):
        return self.entity.serialize()


class GroupEntityRights():

    def __init__(self, group_id=None, entity_rights=None):
        if entity_rights is None:
            self.entity = EntityRights()
            self.entity.resource_type = ResourceType.GROUP
            self.entity.resource_id = group_id
        else:
            self.entity = entity_rights

        # Retrieve owner, manager and member rights
        owner_right = AccessRights.query.filter(
            AccessRights.access_right == AccessRights.OWNER).first()
        manager_right = AccessRights.query.filter(
            AccessRights.access_right == AccessRights.MANAGER).first()
        member_right = AccessRights.query.filter(
            AccessRights.access_right == AccessRights.MEMBER).first()

        self.entity.available_rights = []

        if owner_right is not None and manager_right is not None and member_right is not None:
            self.entity.available_rights.append(
                AccessRightsSelectable(owner_right))
            self.entity.available_rights.append(
                AccessRightsSelectable(manager_right))
            self.entity.available_rights.append(
                AccessRightsSelectable(member_right))

    def add_access_db_object(self, access_db_object, user_id):

        entity_object = None
        entity_type = ''

        if isinstance(access_db_object, GroupAccessGroup):

            entity_type = EntityType.GROUP
            entity_object = Group.query.filter_by(
                id=access_db_object.group_member_id).first()

            if entity_object is None:
                raise EntityRightsError(
                    f'Group object id {access_db_object.group_id} not found.')

        elif isinstance(access_db_object, GroupAccessUser):

            entity_type = EntityType.USER
            entity_object = User.query.filter_by(
                id=access_db_object.user_id).first()

            if entity_object is None:
                raise EntityRightsError(
                    f'User object id {access_db_object.user_id} not found.')

        else:
            raise EntityRightsError(
                f'ProcessEntityRights setup error, bad access_db_object.\n GroupAccessGroup or GroupAccessUser '
                f'intended but {type(access_db_object)} given')

        new_entity_right = EntityRight()
        new_entity_right.entity_type = entity_type
        new_entity_right.id = access_db_object.id
        new_entity_right.entity_object = entity_object
        new_entity_right.selected_right = access_db_object.right_id

        owner_query = AccessRights.query.filter(
            AccessRights.access_right == AccessRights.OWNER).first()
        if owner_query is not None:
            if new_entity_right.selected_right == owner_query.id:
                new_entity_right.locked = True

        if isinstance(access_db_object, GroupAccessUser):
            if new_entity_right.entity_object.id == user_id:
                new_entity_right.locked = True

        self.entity.entities_rights.append(new_entity_right)

    def apply_db_changes(self, db_session, user_id):

        for ent_changes in self.entity.entities_rights:

            if ent_changes.entity_type == EntityType.GROUP:
                self.change_group_group(db_session, ent_changes)

            elif ent_changes.entity_type == EntityType.USER:
                self.change_group_user(db_session, ent_changes, user_id)

    def change_group_group(self, db_session, entity_change):
        if entity_change.id == -1:  # New object to create
            new_object = GroupAccessGroup()
            new_object.group_id = self.entity.resource_id
            new_object.group_member_id = entity_change.entity_object.id
            new_object.right_id = entity_change.selected_right
            new_object.group_members_ids = ResourceAccess.generate_group_members_ids(
                entity_change.entity_object.id)

            db_session.add(new_object)

            # update the impacted group_members_ids
            ResourceAccess.update_group_members_ids(
                new_object.group_id)

        else:  # Update or remove object from database
            if entity_change.selected_right is not None:  # Update object
                update_object = GroupAccessGroup.query.filter(
                    GroupAccessGroup.id == entity_change.id).first()

                if update_object is not None:
                    self.check_not_owner(update_object)
                    update_object.right_id = entity_change.selected_right
                    # in case of right update, there is no change in the group_members_ids

            else:  # Remove object
                self.check_not_last_owner_or_manager(entity_change)
                delete_object = GroupAccessGroup.query.filter(
                    GroupAccessGroup.id == entity_change.id).first()

                if delete_object is not None:
                    db_session.delete(delete_object)
                    # all group_access_group impacted by this relation need to have their group_members_ids updated
                    ResourceAccess.update_group_members_ids(
                        delete_object.group_member_id, delete_object.id)

    def change_group_user(self, db_session, entity_change, user_id):
        if entity_change.id == -1:  # New object to create
            new_object = GroupAccessUser()
            new_object.user_id = entity_change.entity_object.id
            new_object.group_id = self.entity.resource_id
            new_object.right_id = entity_change.selected_right

            db_session.add(new_object)

        else:  # Update or remove object from database
            if entity_change.selected_right is not None:  # Update object
                check_not_current_user(entity_change.entity_object.id, user_id)
                update_object = GroupAccessUser.query.filter(
                    GroupAccessUser.id == entity_change.id).first()

                if update_object is not None:
                    self.check_not_owner(update_object)
                    update_object.right_id = entity_change.selected_right

            else:  # Remove object
                self.check_not_last_owner_or_manager(entity_change)
                delete_object = GroupAccessUser.query.filter(
                    GroupAccessUser.id == entity_change.id).first()

                if delete_object is not None:
                    db_session.delete(delete_object)

    def check_not_last_owner_or_manager(self, entity_change):

        # Get manager right id
        owner_right = AccessRights.query.filter(
            AccessRights.access_right == AccessRights.OWNER).first()

        manager_right = AccessRights.query.filter(
            AccessRights.access_right == AccessRights.MANAGER).first()

        if owner_right is not None and manager_right is not None:

            # Check entity id right is manager
            if entity_change.entity_type == EntityType.GROUP:
                entity_tested = GroupAccessGroup.query.filter(
                    GroupAccessGroup.id == entity_change.id).first()

                if entity_tested is not None:
                    if entity_tested.right_id == owner_right.id:
                        if self.count_owner_and_managers() <= 1:
                            raise EntityRightsError(
                                'You cannot delete the last manager of a group')

            elif entity_change.entity_type == EntityType.USER:
                entity_tested = GroupAccessUser.query.filter(
                    GroupAccessUser.id == entity_change.id).first()

                if entity_tested is not None:
                    if entity_tested.right_id == owner_right.id:
                        if self.count_owner_and_managers() <= 1:
                            raise EntityRightsError(
                                'You cannot delete the last manager of a group')

    def count_owner_and_managers(self):
        users = GroupAccessUser.query.join(AccessRights).filter(
            GroupAccessUser.group_id == self.entity.resource_id).filter(
            or_(AccessRights.access_right == AccessRights.OWNER,
                AccessRights.access_right == AccessRights.MANAGER)).all()

        groups = GroupAccessGroup.query.join(AccessRights).filter(
            GroupAccessGroup.group_id == self.entity.resource_id).filter(
            or_(AccessRights.access_right == AccessRights.OWNER,
                AccessRights.access_right == AccessRights.MANAGER)).all()

        return len(users) + len(groups)

    @staticmethod
    def check_not_owner(update_object):
        owner_query = AccessRights.query.filter(
            AccessRights.access_right == AccessRights.OWNER).first()

        if owner_query is not None:
            if update_object.right_id == owner_query.id:
                raise EntityRightsError(
                    f'Owner right cannot be changed.')
        else:
            raise EntityRightsError(
                f'Owner right cannot be found in database.')

    @staticmethod
    def check_not_current_user(update_object, user_id):
        pass

    def serialize(self):
        return self.entity.serialize()


class StudyCaseEntityRights():

    def __init__(self, study_id=None, entity_rights=None):
        if entity_rights is None:
            self.entity = EntityRights()
            self.entity.resource_type = ResourceType.STUDYCASE
            self.entity.resource_id = study_id
        else:
            self.entity = entity_rights

        # Retrieve owner, manager and member rights
        owner_right = AccessRights.query.filter(
            AccessRights.access_right == AccessRights.OWNER).first()
        manager_right = AccessRights.query.filter(
            AccessRights.access_right == AccessRights.MANAGER).first()
        contributor_right = AccessRights.query.filter(
            AccessRights.access_right == AccessRights.CONTRIBUTOR).first()
        commenter_right = AccessRights.query.filter(
            AccessRights.access_right == AccessRights.COMMENTER).first()
        restricted_viewer_right = AccessRights.query.filter(
            AccessRights.access_right == AccessRights.RESTRICTED_VIEWER).first()

        self.entity.available_rights = []

        if owner_right is not None and manager_right is not None and contributor_right is not None\
                and commenter_right is not None and restricted_viewer_right is not None:
            self.entity.available_rights.append(
                AccessRightsSelectable(owner_right))
            self.entity.available_rights.append(
                AccessRightsSelectable(manager_right))
            self.entity.available_rights.append(
                AccessRightsSelectable(contributor_right))
            self.entity.available_rights.append(
                AccessRightsSelectable(commenter_right))
            self.entity.available_rights.append(
                AccessRightsSelectable(restricted_viewer_right))

    def add_access_db_object(self, access_db_object, user_id):

        entity_object = None
        entity_type = ''

        if isinstance(access_db_object, StudyCaseAccessGroup):

            entity_type = EntityType.GROUP
            entity_object = Group.query.filter_by(
                id=access_db_object.group_id).first()

            if entity_object is None:
                raise EntityRightsError(
                    f'Group object id {access_db_object.group_id} not found.')

        elif isinstance(access_db_object, StudyCaseAccessUser):

            entity_type = EntityType.USER
            entity_object = User.query.filter_by(
                id=access_db_object.user_id).first()

            if entity_object is None:
                raise EntityRightsError(
                    f'User object id {access_db_object.user_id} not found.')

        else:
            raise EntityRightsError(
                f'ProcessEntityRights setup error, bad access_db_object.\n StudyCaseAccessGroup or StudyCaseAccessUser '
                f'intended but {type(access_db_object)} given')

        new_entity_right = EntityRight()
        new_entity_right.entity_type = entity_type
        new_entity_right.id = access_db_object.id
        new_entity_right.entity_object = entity_object
        new_entity_right.selected_right = access_db_object.right_id

        owner_query = AccessRights.query.filter(
            AccessRights.access_right == AccessRights.OWNER).first()
        if owner_query is not None:
            if new_entity_right.selected_right == owner_query.id:
                new_entity_right.locked = True

        if isinstance(access_db_object, StudyCaseAccessUser):
            if new_entity_right.entity_object.id == user_id:
                new_entity_right.locked = True

        self.entity.entities_rights.append(new_entity_right)

    def apply_db_changes(self, db_session, user_id):

        for ent_changes in self.entity.entities_rights:

            if ent_changes.entity_type == EntityType.GROUP:
                self.change_study_group(db_session, ent_changes)

            elif ent_changes.entity_type == EntityType.USER:
                self.change_study_user(db_session, ent_changes, user_id)

    def change_study_group(self, db_session, entity_change):
        if entity_change.id == -1:  # New object to create
            new_object = StudyCaseAccessGroup()
            new_object.group_id = entity_change.entity_object.id
            new_object.study_case_id = self.entity.resource_id
            new_object.right_id = entity_change.selected_right

            db_session.add(new_object)

        else:  # Update or remove object from database
            if entity_change.selected_right is not None:  # Update object
                update_object = StudyCaseAccessGroup.query.filter(
                    StudyCaseAccessGroup.id == entity_change.id).first()

                if update_object is not None:
                    update_object.right_id = entity_change.selected_right

            else:  # Remove object
                self.check_not_last_owner_or_manager(entity_change)
                delete_object = StudyCaseAccessGroup.query.filter(
                    StudyCaseAccessGroup.id == entity_change.id).first()

                if delete_object is not None:
                    db_session.delete(delete_object)

    def change_study_user(self, db_session, entity_change, user_id):
        if entity_change.id == -1:  # New object to create
            new_object = StudyCaseAccessUser()
            new_object.user_id = entity_change.entity_object.id
            new_object.study_case_id = self.entity.resource_id
            new_object.right_id = entity_change.selected_right

            db_session.add(new_object)

        else:  # Update or remove object from database
            if entity_change.selected_right is not None:  # Update object
                check_not_current_user(entity_change.entity_object.id, user_id)
                update_object = StudyCaseAccessUser.query.filter(
                    StudyCaseAccessUser.id == entity_change.id).first()

                if update_object is not None:
                    self.check_not_owner(update_object)
                    update_object.right_id = entity_change.selected_right

            else:  # Remove object
                self.check_not_last_owner_or_manager(entity_change)
                delete_object = StudyCaseAccessUser.query.filter(
                    StudyCaseAccessUser.id == entity_change.id).first()

                if delete_object is not None:
                    db_session.delete(delete_object)

    def check_not_last_owner_or_manager(self, entity_change):

        # Get manager right id
        owner_right = AccessRights.query.filter(
            AccessRights.access_right == AccessRights.OWNER).first()

        manager_right = AccessRights.query.filter(
            AccessRights.access_right == AccessRights.MANAGER).first()

        if owner_right is not None and manager_right is not None:

            # Check entity id right is manager
            if entity_change.entity_type == EntityType.GROUP:
                entity_tested = StudyCaseAccessGroup.query.filter(
                    StudyCaseAccessGroup.id == entity_change.id).first()

                if entity_tested is not None:
                    if entity_tested.right_id == owner_right.id:
                        if self.count_owner_and_managers() <= 1:
                            raise EntityRightsError(
                                'You cannot delete the last manager of a group')

            elif entity_change.entity_type == EntityType.USER:
                entity_tested = StudyCaseAccessUser.query.filter(
                    StudyCaseAccessUser.id == entity_change.id).first()

                if entity_tested is not None:
                    if entity_tested.right_id == owner_right.id:
                        if self.count_owner_and_managers() <= 1:
                            raise EntityRightsError(
                                'You cannot delete the last manager of a group')

    def count_owner_and_managers(self):
        users = StudyCaseAccessUser.query.join(AccessRights).filter(
            StudyCaseAccessUser.group_id == self.entity.resource_id).filter(
            or_(AccessRights.access_right == AccessRights.OWNER,
                AccessRights.access_right == AccessRights.MANAGER)).all()

        groups = StudyCaseAccessGroup.query.join(AccessRights).filter(
            StudyCaseAccessGroup.group_id == self.entity.resource_id).filter(
            or_(AccessRights.access_right == AccessRights.OWNER,
                AccessRights.access_right == AccessRights.MANAGER)).all()

        return len(users) + len(groups)

    @staticmethod
    def check_not_owner(update_object):
        owner_query = AccessRights.query.filter(
            AccessRights.access_right == AccessRights.OWNER).first()

        if owner_query is not None:
            if update_object.right_id == owner_query.id:
                raise EntityRightsError(
                    f'Owner right cannot be changed.')
        else:
            raise EntityRightsError(
                f'Owner right cannot be found in database.')

    @staticmethod
    def check_not_current_user(update_object, user_id):
        pass

    def serialize(self):
        return self.entity.serialize()