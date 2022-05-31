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
from sos_trades_api.tools.right_management.functional.process_access_right import ProcessAccess
from sos_trades_api.tools.right_management.functional.group_access_right import GroupAccess
from sos_trades_api.models.database_models import \
    ProcessAccessUser, ProcessAccessGroup, AccessRights, GroupAccessUser, GroupAccessGroup, User, StudyCaseAccessUser, \
    StudyCaseAccessGroup

from sos_trades_api.base_server import db, app
from sos_trades_api.models.entity_rights import \
    ProcessEntityRights, ResourceType, EntityRightsError, apply_entity_rights_changes, \
    GroupEntityRights, StudyCaseEntityRights
from sos_trades_api.tools.right_management.access_right import has_access_to
from sos_trades_api.tools.right_management import access_right
from sos_trades_api.tools.right_management.functional.study_case_access_right import StudyCaseAccess


def apply_entities_changes(user_id, user_profile_id, entity_rights):
    """
    Save entity right changes for a user
    """
    with app.app_context():

        db_session = db.session

        try:
            if verify_user_authorised_for_resource(user_id, user_profile_id, entity_rights):
                apply_entity_rights_changes(db_session, entity_rights, user_id)
                db_session.commit()

        except Exception as error:
            db_session.rollback()
            raise EntityRightsError(str(error))

        return 'Rights have been successfully updated in database'


def get_study_case_entities_rights(user_id, study_id):
    """
    Get the rights of a user on a study
    """
    study = StudyCaseAccess(user_id)
    study_entity = StudyCaseEntityRights(study_id=study_id)

    # Only process manager can request this
    if study.check_user_right_for_study(AccessRights.MANAGER, study_id=study_id):
        with app.app_context():

            # Retrieve process access on user
            study_cases_access_users = StudyCaseAccessUser.query.filter(
                StudyCaseAccessUser.study_case_id == study_id).all()

            for study_access in study_cases_access_users:
                study_entity.add_access_db_object(study_access, user_id)

            # Retrieve process access on group
            study_cases_access_groups = StudyCaseAccessGroup.query.filter(
                StudyCaseAccessGroup.study_case_id == study_id).all()

            for study_access in study_cases_access_groups:
                study_entity.add_access_db_object(study_access, user_id)

        return study_entity


def get_process_entities_rights(user_id, user_profile_id, process_id):
    """
    Get the rights of a user on a process
    """
    process = ProcessAccess(user_id)
    process_entity = ProcessEntityRights(process_id=process_id)

    # Only process manager or study manager profile can request this
    if process.check_user_right_for_process(AccessRights.MANAGER, process_id=process_id) or \
            has_access_to(user_profile_id, access_right.APP_MODULE_STUDY_MANAGER):
        with app.app_context():

            # Retrieve process access on user
            processes_access_users = ProcessAccessUser.query.filter(
                ProcessAccessUser.process_id == process_id).all()

            for process_access in processes_access_users:
                process_entity.add_access_db_object(process_access, user_id)

            # Retrieve process access on group
            processes_access_groups = ProcessAccessGroup.query.filter(
                ProcessAccessGroup.process_id == process_id).all()

            for process_access in processes_access_groups:
                process_entity.add_access_db_object(process_access, user_id)

        return process_entity


def get_group_entities_rights(user_id, group_id):
    """
    Get the rights of a user on a group
    """
    group = GroupAccess(user_id)
    group_entity = GroupEntityRights(group_id=group_id)

    # Only group manager and owners can request this
    if group.check_user_right_for_group(AccessRights.MANAGER, group_id=group_id) or group.check_user_right_for_group(
            AccessRights.OWNER, group_id=group_id):
        with app.app_context():

            # Retrieve process access on user
            group_access_users = GroupAccessUser.query.filter(
                GroupAccessUser.group_id == group_id).all()

            for group_access in group_access_users:
                group_entity.add_access_db_object(group_access, user_id)

            # Retrieve process access on group
            group_access_groups = GroupAccessGroup.query.filter(
                GroupAccessGroup.group_id == group_id).all()

            for group_access in group_access_groups:
                group_entity.add_access_db_object(group_access, user_id)

        return group_entity


def verify_user_authorised_for_resource(user_id, user_profile_id, entity_rights):
    """
    Check if the user has the MANAGER or OWNER rights for a resources lists
    """
    # PROCESS RESOURCE
    if entity_rights['resourceType'] == ResourceType.PROCESS:
        process = ProcessAccess(user_id)
        # only process manager can request this
        return has_access_to(user_profile_id, access_right.APP_MODULE_STUDY_MANAGER) or \
               process.check_user_right_for_process(AccessRights.MANAGER, process_id=entity_rights['resourceId'])

    # GROUP RESOURCE
    elif entity_rights['resourceType'] == ResourceType.GROUP:
        group = GroupAccess(user_id)
        # only process manager can request this

        if group.check_user_right_for_group(AccessRights.MANAGER, group_id=entity_rights['resourceId']) \
                or group.check_user_right_for_group(AccessRights.OWNER, group_id=entity_rights['resourceId']):
            return True
        else:
            return False

    # STUDYCASE RESOURCE
    elif entity_rights['resourceType'] == ResourceType.STUDYCASE:
        study = StudyCaseAccess(user_id)
        # only process manager can request this
        return study.check_user_right_for_study(AccessRights.MANAGER, study_id=entity_rights['resourceId'])

    # SOSDISCIPLINE RESOURCE
    elif entity_rights['resourceType'] == ResourceType.SOSDISCIPLINE:
        return True

