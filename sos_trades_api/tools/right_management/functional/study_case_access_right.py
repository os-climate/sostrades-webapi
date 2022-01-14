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
from sos_trades_api.models.database_models import \
    AccessRights, StudyCase, StudyCaseAccessUser, StudyCaseAccessGroup
from sos_trades_api.models.study_case_dto import StudyCaseDto
from sos_trades_api.tools.right_management.functional.process_access_right import ProcessAccess
from sos_trades_core.tools.sos_logger import SoSLogging
from sos_trades_api.base_server import db

class StudyCaseAccess(ProcessAccess):
    """ Class containing the access right of a group of SoSTrades.
    """

    def __init__(self, user_id):
        """Constructor
        """
        ProcessAccess.__init__(self, user_id)

        # List that contains study visible by the user but only the enabled one
        self.user_study_cases = []

        # List that contains every study visible for the user
        self.__raw_study_case_list = []

        self.retrieve_user_all_study_cases()
        # Initialize execution logger
        self.__logger = SoSLogging(
            'SoS.AccessRight', level=SoSLogging.WARNING).logger

    def retrieve_user_all_study_cases(self):

        # List that contains study visible by the user but only the enabled one
        self.user_study_cases = []

        # List that contains every study visible for the user
        self.__raw_study_case_list = []

        # Retrieve all study_cases authorised directly to user
        user_study_cases = db.session.query(StudyCase, AccessRights) \
            .filter(StudyCase.id == StudyCaseAccessUser.study_case_id) \
            .filter(StudyCaseAccessUser.user_id == self.user_id) \
            .filter(AccessRights.id == StudyCaseAccessUser.right_id).all()

        for ust in user_study_cases:

            # Check user is authorised for process before adding study case
            if len(list(filter(lambda pr: pr.process_id == ust[0].process and pr.repository_id == ust[0].repository,
                               self.user_loaded_process_list))) > 0:

                new_study_dto = StudyCaseDto(ust[0])
                if ust[1].access_right == AccessRights.OWNER \
                        or ust[1].access_right == AccessRights.MANAGER:
                    new_study_dto.is_manager = True
                elif ust[1].access_right == AccessRights.CONTRIBUTOR:
                    new_study_dto.is_contributor = True
                elif ust[1].access_right == AccessRights.COMMENTER:
                    new_study_dto.is_commenter = True
                elif ust[1].access_right == AccessRights.RESTRICTED_VIEWER:
                    new_study_dto.is_restricted_viewer = True

                # Add study in raw list
                self.__raw_study_case_list.append(new_study_dto)

                if not new_study_dto.disabled:
                    self.user_study_cases.append(new_study_dto)

        # store user_group_list_ids
        user_group_ids = [g.id for g in self.user_groups_list]

        # Retrieve all study cases authorised by groups
        group_study_cases = db.session.query(StudyCase, AccessRights) \
            .filter(StudyCase.id == StudyCaseAccessGroup.study_case_id) \
            .filter(StudyCaseAccessGroup.group_id.in_(user_group_ids)) \
            .filter(AccessRights.id == StudyCaseAccessGroup.right_id).all()

        for gsc in group_study_cases:

            if len(list(filter(lambda ugg: ugg.id == gsc[0].id, self.user_study_cases))) > 0:
                # Updating loaded process on already existing group
                updated_study_dto = list(
                    filter(lambda ugg: ugg.id == gsc[0].id, self.user_study_cases))[0]
                if gsc[1].access_right == AccessRights.OWNER \
                        or gsc[1].access_right == AccessRights.MANAGER:
                    updated_study_dto.is_manager = True
                elif gsc[1].access_right == AccessRights.CONTRIBUTOR:
                    updated_study_dto.is_contributor = True
                elif gsc[1].access_right == AccessRights.COMMENTER:
                    updated_study_dto.is_commenter = True
                elif gsc[1].access_right == AccessRights.RESTRICTED_VIEWER:
                    updated_study_dto.is_restricted_viewer = True
            else:
                # Group right allow every study even if user has not the process right (no need to check process right)
                new_study_dto = StudyCaseDto(gsc[0])
                if gsc[1].access_right == AccessRights.OWNER \
                        or gsc[1].access_right == AccessRights.MANAGER:
                    new_study_dto.is_manager = True
                elif gsc[1].access_right == AccessRights.CONTRIBUTOR:
                    new_study_dto.is_contributor = True
                elif gsc[1].access_right == AccessRights.COMMENTER:
                    new_study_dto.is_commenter = True
                elif gsc[1].access_right == AccessRights.RESTRICTED_VIEWER:
                    new_study_dto.is_restricted_viewer = True

                # Add study in raw list
                self.__raw_study_case_list.append(new_study_dto)

                if not new_study_dto.disabled:
                    self.user_study_cases.append(new_study_dto)

        # Sorting user study cases by creation date
        self.user_study_cases = sorted(
            self.user_study_cases, key=lambda sc: sc.creation_date)

    def check_user_right_for_study(self, right_type, study_id=None):
        """ Methods that check that the given user right to have a specific right for a specific study
        """
        has_access = False
        if study_id is not None:

            # Search in complete studies list authorised for user
            study_dto = list(filter(lambda ust: ust.id == study_id, self.__raw_study_case_list))

            if len(study_dto) > 0:
                if right_type == AccessRights.MANAGER:
                    if study_dto[0].is_manager:
                        has_access = True

                elif right_type == AccessRights.CONTRIBUTOR:
                    if study_dto[0].is_manager or study_dto[0].is_contributor:
                        has_access = True

                elif right_type == AccessRights.COMMENTER:
                    if study_dto[0].is_manager or study_dto[0].is_contributor \
                            or study_dto[0].is_commenter:
                        has_access = True

                elif right_type == AccessRights.RESTRICTED_VIEWER:
                    if study_dto[0].is_manager or study_dto[0].is_contributor \
                            or study_dto[0].is_commenter or study_dto[0].is_restricted_viewer:
                        has_access = True

        return has_access

    def get_study_cases_authorised_from_process(self, process, repository):
        # Retrieving study cases shared with user with same process, and minimum right contributor
        studies_authorised_process = list(
            filter(lambda ust: ust.process == process
                   and ust.repository == repository
                   and (ust.is_manager or ust.is_contributor),
                   self.user_study_cases))

        return studies_authorised_process

    def get_user_right_for_study(self, study_id=None):
        right = None
        if study_id is not None:
            # Search in complete studies, specific study
            study_dto = list(filter(lambda ust: ust.id == study_id, self.user_study_cases))
            if len(study_dto) > 0:
                if study_dto[0].is_manager:
                    right = AccessRights.MANAGER
                elif study_dto[0].is_contributor:
                    right = AccessRights.CONTRIBUTOR
                elif study_dto[0].is_commenter:
                    right = AccessRights.COMMENTER
                elif study_dto[0].is_restricted_viewer:
                    right = AccessRights.RESTRICTED_VIEWER
        return right
