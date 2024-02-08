'''
Copyright 2022 Airbus SAS
Modifications on 2023/10/19-2023/11/23 Copyright 2023 Capgemini

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
from sos_trades_api.models.database_models import (
    AccessRights,
    StudyCase,
    StudyCaseAccessUser,
    StudyCaseAccessGroup,
    Group,
)
from sos_trades_api.models.study_case_dto import StudyCaseDto
from sos_trades_api.tools.right_management.functional.process_access_right import (
    ProcessAccess,
)
from sos_trades_api.server.base_server import db


class StudyCaseAccess(ProcessAccess):
    """Class containing the access right for study case regarding a given user in SoSTrades."""

    def __init__(self, user_id, study_case_identifier=None):
        """
        Constructor
        :param user_id: user identifier to manage
        :type user_id: int
        :param study_case_identifier: (Optional) specific study case to check
        """
        super().__init__(user_id)

        self.__reset()

        self.retrieve_user_study_cases(study_case_identifier)

    @property
    def user_study_cases(self):
        """
        Return the list of user available study cases
        :return: sos_trades_api.models.database_models.StudyCaseDto[]
        """
        return list(self._user_study_cases.values())

    def __reset(self):
        """
        Re set members variables
        """
        # List that contains study visible by the user but only the enabled one
        self._user_study_cases = {}

        # List that contains every study visible for the user
        self.__raw_study_case_list = {}

    def retrieve_user_study_cases(self, study_case_identifier=None):
        """
        Retrieve all study cases in database and set access right regarding user for which the request is done
        Algorithm work in three phase
        1 - get study declared for the user directly
        2 - get study case  declared for groups where the user belongs

        :param study_case_identifier: (Optional) is provided limit search to the given study case
        :type study_case_identifier: int
        """
        self.__reset()

        owner_right = AccessRights.query.filter(
            AccessRights.access_right == AccessRights.OWNER
        ).first()

        # Retrieve all study_cases authorised directly to user
        user_study_cases_query = (
            db.session.query(StudyCase, AccessRights, Group)
            .filter(StudyCase.id == StudyCaseAccessUser.study_case_id)
            .filter(StudyCaseAccessUser.user_id == self.user_id)
            .filter(AccessRights.id == StudyCaseAccessUser.right_id)
            .filter(StudyCaseAccessGroup.study_case_id == StudyCase.id)
            .filter(StudyCaseAccessGroup.right_id == owner_right.id)
            .filter(StudyCaseAccessGroup.group_id == Group.id)
        )

        if study_case_identifier is not None:
            user_study_cases_query = user_study_cases_query.filter(
                StudyCase.id == study_case_identifier
            )

        user_study_cases = user_study_cases_query.all()

        for ust in user_study_cases:

            current_study_case = ust[0]
            current_access_rights = ust[1]
            current_owner_group = ust[2]

            # Check user is authorised for process before adding study case
            key = f'{current_study_case.repository}.{current_study_case.process}'

            if key in self._user_loaded_process_list_by_name.keys():

                new_study_dto = StudyCaseDto(current_study_case, current_owner_group)
                if (
                    current_access_rights.access_right == AccessRights.OWNER
                    or current_access_rights.access_right == AccessRights.MANAGER
                ):
                    new_study_dto.is_manager = True
                elif current_access_rights.access_right == AccessRights.CONTRIBUTOR:
                    new_study_dto.is_contributor = True
                elif current_access_rights.access_right == AccessRights.COMMENTER:
                    new_study_dto.is_commenter = True
                elif (
                    current_access_rights.access_right == AccessRights.RESTRICTED_VIEWER
                ):
                    new_study_dto.is_restricted_viewer = True

                # Add study in raw list
                self.__raw_study_case_list[current_study_case.id] = new_study_dto

                if not new_study_dto.disabled:
                    self._user_study_cases[current_study_case.id] = new_study_dto

        # store user_group_list_ids
        user_group_ids = list(self._user_groups_list.keys())

        # Retrieve all study cases authorised by groups
        group_study_cases_query = (
            db.session.query(StudyCase, AccessRights)
            .filter(StudyCase.id == StudyCaseAccessGroup.study_case_id)
            .filter(StudyCaseAccessGroup.group_id.in_(user_group_ids))
            .filter(AccessRights.id == StudyCaseAccessGroup.right_id)
        )

        if study_case_identifier is not None:
            group_study_cases_query = group_study_cases_query.filter(
                StudyCase.id == study_case_identifier
            )

        group_study_cases = group_study_cases_query.all()

        study_case_ids = list([gsc[0].id for gsc in group_study_cases])

        # Retrieve study owner group
        study_case_owner_group = (
            db.session.query(Group, StudyCaseAccessGroup)
            .filter(Group.id == StudyCaseAccessGroup.group_id)
            .filter(StudyCaseAccessGroup.study_case_id.in_(study_case_ids))
            .filter(StudyCaseAccessGroup.right_id == owner_right.id)
            .all()
        )

        study_case_owner_group_dict = {}
        for stog in study_case_owner_group:
            study_case_owner_group_dict[stog[1].study_case_id] = stog[0]

        for gsc in group_study_cases:

            current_study_case_group = gsc[0]
            current_access_rights = gsc[1]


            if current_study_case_group.id in self._user_study_cases:

                # Updating loaded process on already existing group
                new_study_dto = self._user_study_cases[current_study_case_group.id]

            else:

                current_owner_group = study_case_owner_group_dict[
                    current_study_case_group.id
                ]

                # Group right allow every study even if user has not the process right (no need to check process right)
                new_study_dto = StudyCaseDto(
                    current_study_case_group, current_owner_group
                )

                # Add study in raw list
                self.__raw_study_case_list[current_study_case_group.id] = new_study_dto

                if not new_study_dto.disabled:
                    self._user_study_cases[current_study_case_group.id] = new_study_dto

            if (
                current_access_rights.access_right == AccessRights.OWNER
                or current_access_rights.access_right == AccessRights.MANAGER
            ):
                new_study_dto.is_manager = True
            elif current_access_rights.access_right == AccessRights.CONTRIBUTOR:
                new_study_dto.is_contributor = True
            elif current_access_rights.access_right == AccessRights.COMMENTER:
                new_study_dto.is_commenter = True
            elif current_access_rights.access_right == AccessRights.RESTRICTED_VIEWER:
                new_study_dto.is_restricted_viewer = True

    def check_user_right_for_study(self, right_type, study_case_identifier):
        """
        Methods that check that the given user right to have a specific right for a specific study

        :param right_type: type of access right to check
        :type right_type: sos_trades_api.models.database_models.AccessRights
        :param study_case_identifier: study case identifier to check
        :type study_case_identifier: int
        :return: boolean
        """
        has_access = False
        if study_case_identifier is not None:

            # Search in complete studies list authorised for user
            if study_case_identifier in self.__raw_study_case_list:

                study_dto = self.__raw_study_case_list[study_case_identifier]

                if right_type == AccessRights.MANAGER:
                    if study_dto.is_manager:
                        has_access = True

                elif right_type == AccessRights.CONTRIBUTOR:
                    if study_dto.is_manager or study_dto.is_contributor:
                        has_access = True

                elif right_type == AccessRights.COMMENTER:
                    if (
                        study_dto.is_manager
                        or study_dto.is_contributor
                        or study_dto.is_commenter
                    ):
                        has_access = True

                elif right_type == AccessRights.RESTRICTED_VIEWER:
                    if (
                        study_dto.is_manager
                        or study_dto.is_contributor
                        or study_dto.is_commenter
                        or study_dto.is_restricted_viewer
                    ):
                        has_access = True

        return has_access

    def get_study_cases_authorised_from_process(self, process_name, repository_name):
        """
        Retrieving study cases shared with user with same process, and minimum right contributor

        :param process_name: Name of the process to check right for user
        :type process_name: str
        :param repository_name: Repository of the process to check right for user
        :type repository_name: str
        :return: sos_trades_api.models.database_models.StudyCaseDto[]
        """
        #
        studies_authorised_process = list(
            filter(
                lambda ust: ust.process == process_name
                and ust.repository == repository_name
                and (ust.is_manager or ust.is_contributor),
                self._user_study_cases.values(),
            )
        )

        return studies_authorised_process

    def get_user_right_for_study(self, study_case_identifier):
        """
        Get user rights for the given study_case_identifier

        :param study_case_identifier: study case identifier for which user rights will be retrieve
        :type study_case_identifier: int
        :return: sos_trades_api.models.database_models.AccessRights or None
        """
        right = None
        if study_case_identifier is not None:

            # Search in complete studies, specific study
            if study_case_identifier in self._user_study_cases:
                study_dto = self._user_study_cases[study_case_identifier]

                if study_dto.is_manager:
                    right = AccessRights.MANAGER
                elif study_dto.is_contributor:
                    right = AccessRights.CONTRIBUTOR
                elif study_dto.is_commenter:
                    right = AccessRights.COMMENTER
                elif study_dto.is_restricted_viewer:
                    right = AccessRights.RESTRICTED_VIEWER
        return right
