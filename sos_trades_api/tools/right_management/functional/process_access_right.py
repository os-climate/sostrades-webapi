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

from sos_trades_api.models.database_models import Process, ProcessAccessUser, \
    ProcessAccessGroup, AccessRights
from sos_trades_api.tools.right_management.functional.tools_access_right import ResourceAccess
from sos_trades_api.models.loaded_process import LoadedProcess
from sos_trades_api.base_server import db


class ProcessAccess(ResourceAccess):
    """ Class containing the access right of a process of SoSTrades.
    """

    def __init__(self, user_id):
        """Constructor
        """
        ResourceAccess.__init__(self, user_id)
        self.user_process_list = []
        self.user_loaded_process_list = []
        self.retrieve_user_all_process_rights()

    def retrieve_user_all_process_rights(self):
        """
        Retrieve all process in database and set access right regarding user for which the request is done
        Algorithm work in three phase
        1 - get process declared for the user
        2 - get process declared for groups where the user belongs
        3 - add all non accessible process (no rights but listed anyway)
        :return:
        """

        # Manage retrieving of process where the user is declared
        user_process_list = db.session.query(Process, AccessRights) \
            .filter(Process.id == ProcessAccessUser.process_id) \
            .filter(ProcessAccessUser.user_id == self.user_id) \
            .filter(AccessRights.id == ProcessAccessUser.right_id).all()

        for ups in user_process_list:
            # Adding process to process list
            self.user_process_list.append(ups[0])
            # Adding process to loaded process list

            new_loaded_process = LoadedProcess(
                ups[0].id, ups[0].name, ups[0].process_path)

            if ups[1].access_right == AccessRights.MANAGER:
                new_loaded_process.is_manager = True
            elif ups[1].access_right == AccessRights.CONTRIBUTOR:
                new_loaded_process.is_contributor = True
            self.user_loaded_process_list.append(new_loaded_process)

        # store user_group_list_ids
        user_group_ids = [g.id for g in self.user_groups_list]

        # Manage retrieving of process where the user belong to q declared groups
        # retrieve all process authorised by groups
        group_process_list = db.session.query(Process, AccessRights) \
            .filter(Process.id == ProcessAccessGroup.process_id) \
            .filter(ProcessAccessGroup.group_id.in_(user_group_ids)) \
            .filter(AccessRights.id == ProcessAccessGroup.right_id).all()

        for gpl in group_process_list:
            if len(list(filter(lambda ugg: ugg.id == gpl[0].id, self.user_process_list))) > 0:
                # Updating loaded process on already existing process
                updated_loaded_process = list(
                    filter(lambda ugg: ugg.id == gpl[0].id, self.user_loaded_process_list))[0]
                if gpl[1].access_right == AccessRights.MANAGER:
                    updated_loaded_process.is_manager = True
                elif gpl[1].access_right == AccessRights.CONTRIBUTOR:
                    updated_loaded_process.is_contributor = True
            else:
                # Adding process to process list
                self.user_process_list.append(gpl[0])

                new_loaded_process = LoadedProcess(
                    gpl[0].id, gpl[0].name, gpl[0].process_path)

                if gpl[1].access_right == AccessRights.MANAGER:
                    new_loaded_process.is_manager = True
                elif gpl[1].access_right == AccessRights.CONTRIBUTOR:
                    new_loaded_process.is_contributor = True
                self.user_loaded_process_list.append(new_loaded_process)

        # Add all other process with no rights
        all_processes = Process.query.all()

        # Get all process already in the user list
        already_manage_processes_identifier = [loaded_process.id for loaded_process in self.user_loaded_process_list]
        for one_process in all_processes:

            if one_process.id not in already_manage_processes_identifier:
                new_loaded_process = LoadedProcess(
                    one_process.id, one_process.name, one_process.process_path)
                new_loaded_process.is_manager = False
                new_loaded_process.is_contributor = False
                self.user_loaded_process_list.append(new_loaded_process)

        # Sorting lists by process repository
        self.user_process_list = sorted(
            self.user_process_list, key=lambda pr: pr.process_path.lower())
        self.user_loaded_process_list = sorted(
            self.user_loaded_process_list, key=lambda pl: pl.repository_id.lower())

    def check_user_right_for_process(self, right_type, process_name=None, repository_name=None, process_id=None):
        """ Methods that check that the given user right to have a specific right for a specific process
        """
        has_access = False
        if (process_name is not None and repository_name is not None) or (process_id is not None):

            right_entity_number = 0

            # retrieve process id
            if process_name is not None and repository_name is not None:
                current_process = Process.query.filter(
                    Process.name == process_name, Process.process_path == repository_name).first()
            elif process_id is not None:
                current_process = Process.query.filter(
                    Process.id == process_id).first()

            if current_process is not None:
                if len(list(filter(lambda lop: lop.id == current_process.id,
                                   self.user_loaded_process_list))) > 0:
                    loaded_process = list(filter(lambda lop: lop.id == current_process.id,
                                                 self.user_loaded_process_list))[0]
                    if loaded_process is not None:
                        if loaded_process.is_manager:
                            has_access = True
                        elif right_type == AccessRights.CONTRIBUTOR and loaded_process.is_contributor:
                            has_access = True
        return has_access

    def get_process_from_name(self, process_name=None, repository_name=None):
        """ Methods that retrieve a process from its name and repository

        """
        if process_name is not None and repository_name is not None:

            process = Process.query.filter(
                Process.name == process_name, Process.process_path == repository_name).first()
            if process is None:
                self.__logger.warning(
                    f'Impossible to find process {process_name} in repository {repository_name} in the database')

            return process
        else:
            return None

    def get_authorized_process(self, with_disabled_process=False):
        """ Regarding Process in database, check if the current has access to them

        :params: with_disabled_process, check with disabled process or not
        :type: boolean

        :return: Process[]
        """
        authorized_process_list = []

        all_processes = Process.query.filter(
            Process.disabled == with_disabled_process).all()

        for process in all_processes:
            loaded_process = list(filter(
                lambda lop: lop.repository_id == process.process_path and lop.process_id == process.name,
                self.user_loaded_process_list))

            if len(loaded_process) > 0:
                authorized_process_list.append(loaded_process[0])

            if len(authorized_process_list) > 0:
                authorized_process_list = sorted(
                    authorized_process_list, key=lambda ap: ap.repository_name.lower())

        return authorized_process_list
