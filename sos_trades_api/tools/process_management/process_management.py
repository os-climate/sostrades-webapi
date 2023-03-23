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
Process management
"""
from sos_trades_api.server.base_server import db
from sqlalchemy import and_
from sostrades_core.sos_processes.processes_factory import SoSProcessFactory
from sos_trades_api.models.database_models import Process, AccessRights, \
    ProcessAccessUser, ProcessAccessGroup, StudyCase, User, Group
from sos_trades_api.tools.right_management.functional import process_access_right


def update_database_with_process(additional_repository_list=None, logger=None, default_manager_user=None,
                                 default_manager_group=None):
    """ Method that retrieve all available processes and inject them into database
    If a process already exist in database it will be enabled or disabled regarding
    is the process is found into the source code


    The methods check for processes using:

    - The PYTHONPATH environment variable
    - A list set in flask server configuration ('SOS_TRADES_PROCESS_REPOSITORY' key)

    :param additional_repository_list: list with additional repository to load
    :type additional_repository_list: list[str]

    :param logger: logging message
    :type logger: logging.Logger

    :param default_manager_user: user to set with manager right on processes
    :type default_manager_user: sos_trades_api.models.database_models.User

    :param default_manager_group: group to set with manager right on processes
    :type default_manager_group: sos_trades_api.models.database_models.Group

    """

    # Retrieve all process list
    process_factory = SoSProcessFactory(
        additional_repository_list=additional_repository_list, logger=logger)

    # Get processes dictionary
    processes_dict = process_factory.get_processes_dict()
    logger.info(
        f'{len(processes_dict)} repository found.')

    # Get all default process access rights from repository files
    default_user_rights = process_factory.get_user_default_rights_dict()
    default_group_rights = process_factory.get_group_default_rights_dict()

    # Retrieve all existing process from database
    all_database_processes = Process.query.all()

    # Disabled all existing process
    for database_process in all_database_processes:
        database_process.disabled = True
        db.session.add(database_process)
    logger.info(
        f'{len(all_database_processes)} existing process disabled found')

    # Retrieve all existing process user access created from repository file
    all_database_process_access_user = ProcessAccessUser.query.filter(
        ProcessAccessUser.source == ProcessAccessUser.SOURCE_FILE)
    all_database_process_access_group = ProcessAccessGroup.query.filter(
        ProcessAccessGroup.source == ProcessAccessGroup.SOURCE_FILE)

    # Remove all existing default access rights to add only existing ones
    logger.info(
        f'{all_database_process_access_user.count()} existing default ProcessAccessUser to delete')
    logger.info(
        f'{all_database_process_access_group.count()} existing default ProcessAccessGroup to delete')
    for process_access_user in all_database_process_access_user:
        db.session.delete(process_access_user)
    for process_access_group in all_database_process_access_group:
        db.session.delete(process_access_group)

    # Retrieve manager access profile for process rights
    manager_right = AccessRights.query.filter(
        AccessRights.access_right == AccessRights.MANAGER).first()

    new_process_count = 0
    enabled_process_count = 0
    new_process_access_user_count = 0
    new_process_access_group_count = 0

    for process_module, process_names in processes_dict.items():
        for process_name in process_names:

            loaded_process = list(
                filter(lambda p: p.process_path == process_module and p.name == process_name, all_database_processes))

            if len(loaded_process) > 0:

                if len(loaded_process) == 1:
                    existing_process = loaded_process[0]
                else:
                    # Remove last entry in duplicate
                    loaded_process_sorted = sorted(
                        loaded_process, key=lambda proc: proc.id)
                    for i in range(1, len(loaded_process_sorted)):
                        logger.info(f'Removed one duplicate entry for process {loaded_process_sorted[i].name} '
                                    f'with path {loaded_process_sorted[i].process_path}'
                                    f'and id of duplicate {loaded_process_sorted[i].id}')
                        db.session.delete(loaded_process_sorted[i])
                    # Keep initial process
                    existing_process = loaded_process_sorted[0]

                existing_process.disabled = False
                enabled_process_count = enabled_process_count + 1

                db.session.add(existing_process)

                if default_manager_user is not None:
                    set_process_user_right(default_manager_user.id,
                                           existing_process.id, manager_right.id, False)

                if default_manager_group is not None:
                    set_process_group_right(default_manager_group.id,
                                            existing_process.id, manager_right.id, False)

                # Add default right to each group in the default process access
                # files:
                if process_module in default_group_rights.keys():

                    for group_name in default_group_rights[process_module]:
                        # check if group exists in DB
                        group = Group.query.filter(
                            Group.name == group_name).first()
                        if group is not None:
                            new_process_access_group_count += 1
                            set_process_group_right(group.id,
                                                    existing_process.id, manager_right.id, True)

                # Add default right to each user in the default process access
                # files:
                if process_module in default_user_rights.keys():
                    for user_mail in default_user_rights[process_module]:
                        # check if user exists in DB
                        user = User.query.filter(
                            User.email == user_mail).first()
                        if user is not None:
                            process_access_user = process_access_right.ProcessAccess(
                                user.id)
                            # if the user has no access to the process:
                            if process_access_user is not None and not process_access_user.check_user_right_for_process(
                                    right_type=AccessRights.MANAGER, process_id=existing_process.id):
                                new_process_access_user_count += 1
                                set_process_user_right(user.id,
                                                       existing_process.id, manager_right.id, True)
            else:

                # Create a new process
                new_process = Process()
                new_process.process_path = process_module
                new_process.name = process_name
                new_process.disabled = False
                new_process_count = new_process_count + 1
                enabled_process_count = enabled_process_count + 1
                db.session.add(new_process)
                db.session.flush()

                if default_manager_user is not None:
                    # Add manager rights on process for the manager user
                    process_access_user = ProcessAccessUser()
                    process_access_user.user_id = default_manager_user.id
                    process_access_user.process_id = new_process.id
                    process_access_user.right_id = manager_right.id
                    db.session.add(process_access_user)
                    db.session.flush()

                if default_manager_group is not None:
                    # Add manager rights on process for the manager group
                    process_access_group = ProcessAccessGroup()
                    process_access_group.group_id = default_manager_group.id
                    process_access_group.process_id = new_process.id
                    process_access_group.right_id = manager_right.id
                    db.session.add(process_access_group)
                    db.session.flush()

    logger.info(
        f'{new_process_access_user_count} new default ProcessAccessUser added')
    logger.info(
        f'{new_process_access_group_count} new default ProcessAccessGroup added')
    logger.info(f'{new_process_count} new process(es) found')
    logger.info(f'{enabled_process_count} enabled process(es)')

    disabled_process = Process.query.filter(Process.disabled == True).all()
    if len(disabled_process) > 0:
        from sos_trades_api.controllers.sostrades_main.study_case_controller import delete_study_cases
        logger.info(f'{len(disabled_process)} disabled processes found.')

        # Removing for each disabled process, related studycase
        process_ids_to_delete = []
        for process in disabled_process:
            # Save process id in a list
            if process.id not in process_ids_to_delete:
                process_ids_to_delete.append(process.id)
        # Removing for each process, related study case
        for pr_id in process_ids_to_delete:
            # Retrieve process information
            process_deleted = Process.query.filter(Process.id == pr_id).first()
            if process_deleted is not None:
                # Retrieve all study cases associated to process
                sc_process = StudyCase.query \
                    .filter(StudyCase.process == process_deleted.name) \
                    .filter(StudyCase.repository == process_deleted.process_path).all()

                if len(sc_process) > 0:
                    scs_ids_to_delete = []
                    scs_info_deleted = {}
                    for sc in sc_process:
                        if sc.id not in scs_ids_to_delete:
                            scs_ids_to_delete.append(sc.id)
                            scs_info_deleted[sc.id] = sc.name

                    logger.info(f'Deleting study case(s) related to disabled process '
                                f'with id : {process_deleted.id} and name : "{process_deleted.name}"')
                    delete_study_cases(scs_ids_to_delete)
                    for sc_id, sc_name in scs_info_deleted.items():
                        logger.info(
                            f'Removed study case with id : {sc_id} and name : "{sc_name}"')

        logger.info('Start deleting disabled process...')
        disabled_process_to_delete = Process.query.filter(
            Process.disabled == True).all()
        for process in disabled_process_to_delete:
            logger.info(
                f'Removed process with id : {process.id} and name : "{process.name}"')
            db.session.delete(process)

    db.session.commit()


def set_process_user_right(user_id, process_id, right_id, is_source_file):
    """Set specific right on the specified user regarding given process identifier

    If the user_right doesn't already exists, it create a ProcessAccessUser instance with the defined right

    :param user_id: The identifier of the user that needs the right
    :type user_id: int

    :param process_id: the identifier of the process that have the right
    :type process_id: int

    :param right_id: the identifier of the user right related (manager, contributor...)
    :type right_id: int

    :param is_source_file: if this has to be marked has added using repository rights file
    :type is_source_file: bool
    """
    # Check if right already exist for this user
    process_access_user = ProcessAccessUser.query.filter(and_(
        ProcessAccessUser.user_id == user_id,
        ProcessAccessUser.process_id == process_id)).first()

    if process_access_user is None:
        process_access_user = ProcessAccessUser()
        process_access_user.user_id = user_id
        process_access_user.process_id = process_id
        process_access_user.right_id = right_id
        # set the source at file if it is in the default right file of the repo
        # else the default value "USER" is set
        if is_source_file:
            process_access_user.source = ProcessAccessUser.SOURCE_FILE
        db.session.add(process_access_user)
        db.session.flush()
    else:
        process_access_user.right_id = right_id
        if is_source_file:
            process_access_user.source = ProcessAccessUser.SOURCE_FILE
        db.session.flush()


def set_process_group_right(group_id, process_id, right_id, is_source_file):
    """Set specific right on the specified group regarding given process identifier

    If the group_right doesn't already exists, create a ProcessAccessGroup  instancewith the defined right

    :param group_id: The identifier of the user that needs the right
    :type group_id: int

    :param process_id: the identifier of the process that have the right
    :type process_id: int

    :param right_id: the identifier of the user right related (manager, contributor...)
    :type right_id: int

    :param is_source_file: if this has to be marked has added using repository rights file
    :type is_source_file: bool
    """
    # Check if right already exist for this group
    process_access_group = ProcessAccessGroup.query.filter(and_(
        ProcessAccessGroup.group_id == group_id,
        ProcessAccessGroup.process_id == process_id)).first()

    if process_access_group is None:
        process_access_group = ProcessAccessGroup()
        process_access_group.group_id = group_id
        process_access_group.process_id = process_id
        process_access_group.right_id = right_id
        if is_source_file:
            process_access_group.source = ProcessAccessGroup.SOURCE_FILE
        db.session.add(process_access_group)
        db.session.flush()
    else:
        process_access_group.right_id = right_id
        if is_source_file:
            process_access_group.source = ProcessAccessGroup.SOURCE_FILE
        db.session.flush()
