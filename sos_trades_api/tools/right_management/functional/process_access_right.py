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
methods to define access rights for a process
"""

from sos_trades_api.models.database_models import (
    Process,
    ProcessAccessUser,
    ProcessAccessGroup,
    AccessRights,
)
from sos_trades_api.tools.right_management.functional.tools_access_right import (
    ResourceAccess,
)
from sos_trades_api.models.loaded_process import LoadedProcess
from sos_trades_api.server.base_server import db


class ProcessAccess(ResourceAccess):
    """Class containing the access right of processes regarding a user in SoSTrades."""

    def __init__(self, user_id):
        """
        Constructor
        :param user_id: user identifier to manage
        :type user_id: int
        """

        super().__init__(user_id)
        self.__reset()
        self.retrieve_user_all_process_rights()

    def __reset(self):
        """
        Re set members variables
        """
        self._user_process_list = {}
        self._user_loaded_process_list = {}
        self._user_loaded_process_list_by_name = {}

    def __add_loaded_process(self, loaded_process):
        """
        Add loaded process to lists
        :param loaded_process: process to add to the members variables
        :type sos_trades_api.models.loaded_process.LoadedProcess
        """
        self._user_loaded_process_list[loaded_process.id] = loaded_process
        self._user_loaded_process_list_by_name[
            f'{loaded_process.repository_id}.{loaded_process.process_id}'
        ] = loaded_process

    def retrieve_user_all_process_rights(self):
        """
        Retrieve all process in database and set access right regarding user for which the request is done
        Algorithm work in three phase
        1 - get process declared for the user
        2 - get process declared for groups where the user belongs
        3 - add all non accessible process (no rights but listed anyway)
        """

        self.__reset()

        # Manage retrieving of process where the user is declared
        user_process_list = (
            db.session.query(Process, AccessRights)
            .filter(Process.id == ProcessAccessUser.process_id)
            .filter(ProcessAccessUser.user_id == self.user_id)
            .filter(AccessRights.id == ProcessAccessUser.right_id)
            .all()
        )

        for ups in user_process_list:

            current_process = ups[0]
            current_access_rights = ups[1]

            # Adding process to process list
            self._user_process_list[current_process.id] = current_process

            # Adding process to loaded process list
            new_loaded_process = LoadedProcess(
                current_process.id, current_process.name, current_process.process_path
            )

            if current_access_rights.access_right == AccessRights.MANAGER:
                new_loaded_process.is_manager = True
            elif current_access_rights.access_right == AccessRights.CONTRIBUTOR:
                new_loaded_process.is_contributor = True

            self.__add_loaded_process(new_loaded_process)

        # store user_group_list_ids
        user_group_ids = list(self._user_groups_list.keys())

        # Manage retrieving of process where the user belong to q declared groups
        # retrieve all process authorised by groups
        group_process_list = (
            db.session.query(Process, AccessRights)
            .filter(Process.id == ProcessAccessGroup.process_id)
            .filter(ProcessAccessGroup.group_id.in_(user_group_ids))
            .filter(AccessRights.id == ProcessAccessGroup.right_id)
            .all()
        )

        for gpl in group_process_list:
            current_group_process = gpl[0]
            current_access_rights = gpl[1]
            loaded_process_to_manage = None

            if current_group_process.id in self._user_process_list:

                # Updating loaded process on already existing process
                loaded_process_to_manage = self._user_loaded_process_list[
                    current_group_process.id
                ]

            else:
                # Adding process to process list
                self._user_process_list[
                    current_group_process.id
                ] = current_group_process

                loaded_process_to_manage = LoadedProcess(
                    current_group_process.id,
                    current_group_process.name,
                    current_group_process.process_path,
                )

                self.__add_loaded_process(loaded_process_to_manage)

            if current_access_rights.access_right == AccessRights.MANAGER:
                loaded_process_to_manage.is_manager = True
            elif current_access_rights.access_right == AccessRights.CONTRIBUTOR:
                loaded_process_to_manage.is_contributor = True

        # Add all other process with no rights
        all_processes = Process.query.all()

        # Get all process already in the user list
        already_manage_processes_identifier = list(
            self._user_loaded_process_list.keys()
        )

        for one_process in all_processes:

            if one_process.id not in already_manage_processes_identifier:
                new_loaded_process = LoadedProcess(
                    one_process.id, one_process.name, one_process.process_path
                )
                new_loaded_process.is_manager = False
                new_loaded_process.is_contributor = False
                self.__add_loaded_process(new_loaded_process)

    def check_user_right_for_process(
        self, right_type, process_name=None, repository_name=None, process_id=None
    ):
        """
        Methods that check that the given user right to have a specific right for a specific process
        Checked process can be declared using
        - repository and name
        or
        - identifier
        :param right_type: type of access right to check
        :type right_type: sos_trades_api.models.database_models.AccessRights
        :param process_name: Name of the process to check right for user
        :type process_name: str
        :param repository_name: Repository of the process to check right for user
        :type repository_name: str
        :param process_id: Identifier of the process to check right for user
        :type process_id: int
        :return: boolean
        """
        has_access = False
        if (process_name is not None and repository_name is not None) or (
            process_id is not None
        ):

            pass

            # retrieve process id
            if process_name is not None and repository_name is not None:
                current_process = Process.query.filter(
                    Process.name == process_name,
                    Process.process_path == repository_name,
                ).first()
            elif process_id is not None:
                current_process = Process.query.filter(Process.id == process_id).first()

            if current_process is not None:
                if current_process.id in self._user_loaded_process_list:
                    loaded_process = self._user_loaded_process_list[current_process.id]

                    if loaded_process is not None:
                        if loaded_process.is_manager:
                            has_access = True
                        elif (
                            right_type == AccessRights.CONTRIBUTOR
                            and loaded_process.is_contributor
                        ):
                            has_access = True
        return has_access

    def get_process_from_name(self, process_name=None, repository_name=None):
        """
        Methods that retrieve a process from its name and repository

        :param process_name: Name of the process to get
        :type process_name: str
        :param repository_name: Repository of the process to get
        :type repository_name: str
        :return: sos_trades_api.models.database_models.Process or None
        """
        if process_name is not None and repository_name is not None:

            process = Process.query.filter(
                Process.name == process_name, Process.process_path == repository_name
            ).first()
            if process is None:
                self.__logger.warning(
                    f'Impossible to find process {process_name} in repository {repository_name} in the database'
                )

            return process
        else:
            return None

    def get_authorized_process(self, with_disabled_process=False):
        """
        Regarding Process in database, check if the current has access to them

        :param with_disabled_process: check with disabled process or not
        :type with_disabled_process: boolean
        :return: Process[]
        """
        authorized_process_list = []

        all_processes = Process.query.filter(
            Process.disabled == with_disabled_process
        ).all()

        for process in all_processes:

            if process.id in self._user_loaded_process_list:
                authorized_process_list.append(
                    self._user_loaded_process_list[process.id]
                )

        if len(authorized_process_list) > 0:
            authorized_process_list = sorted(
                authorized_process_list, key=lambda ap: ap.repository_name.lower()
            )

        return authorized_process_list
