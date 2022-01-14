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
Class that represent a study case data transfert object with group information
"""
from sos_trades_api.models.database_models import Group, StudyCaseAccessGroup, \
    StudyCase, AccessRights


class StudyCaseDto:

    def __init__(self, study_case_instance=None):
        """ Initialize DTO using a study case instance

        :params: study_case_instance, instance of database study case
        :type: sostrades_webapi.models.database_models.StudyCase
        """

        self.id = None
        self.name = ''
        self.process = ''
        self.repository = ''
        self.process_display_name = ''
        self.repository_display_name = ''
        self.creation_date = ''
        self.modification_date = ''
        self.study_type = ''
        self.group_name = ''
        self.group_id = None
        self.group_confidential = ''
        self.is_reference_running = False
        self.regeneration_id = None
        self.regeneration_status = None
        self.is_manager = False
        self.is_contributor = False
        self.is_commenter = False
        self.is_restricted_viewer = False
        self.disabled = False


        if study_case_instance is not None:
            self.id = study_case_instance.id
            self.name = study_case_instance.name
            self.process = study_case_instance.process
            self.repository = study_case_instance.repository
            self.creation_date = study_case_instance.creation_date
            self.modification_date = study_case_instance.modification_date
            self.process_display_name = study_case_instance.process
            self.repository_display_name = study_case_instance.repository
            self.disabled = study_case_instance.disabled
            self.study_type = 'Study'


            # Retrieve group owner
            owner_right = AccessRights.query.filter(
                AccessRights.access_right == AccessRights.OWNER).first()
            if owner_right is not None:
                group = Group.query.join(StudyCaseAccessGroup)\
                    .filter(StudyCaseAccessGroup.study_case_id == study_case_instance.id)\
                    .filter(StudyCaseAccessGroup.right_id == owner_right.id)\
                    .first()

                if group is not None:
                    self.group_name = group.name
                    self.group_id = group.id
                    self.group_confidential = group.confidential

    def apply_ontology(self, process_metadata, repository_metadata):

        process_key = f'{self.repository}.{self.process}'

        if process_metadata is not None and process_key in process_metadata:
            if process_metadata[process_key].get('label', None) is not None:
                self.process_display_name = process_metadata[process_key]['label']

        if repository_metadata is not None and self.repository in repository_metadata:
            if repository_metadata[self.repository].get('label', None) is not None:
                self.repository_display_name = repository_metadata[self.repository]['label']

    def serialize(self):
        """ json serializer for dto purpose
        """
        result = {}
        result.update({'id': self.id})
        result.update({'name': self.name})
        result.update({'process': self.process})
        result.update({'repository': self.repository})
        result.update({'process_display_name': self.process_display_name})
        result.update({'repository_display_name': self.repository_display_name})
        result.update({'creation_date': self.creation_date})
        result.update({'modification_date': self.modification_date})
        result.update({'study_type': self.study_type})
        result.update({'group_name': self.group_name})
        result.update({'group_id': self.group_id})
        result.update({'group_confidential': self.group_confidential})
        result.update({'is_reference_running': self.is_reference_running})
        result.update({'regeneration_id': self.regeneration_id})
        result.update({'regeneration_status': self.regeneration_status})
        result.update({'is_manager': self.is_manager})
        result.update({'is_contributor': self.is_contributor})
        result.update({'is_commenter': self.is_commenter})
        result.update({'is_restricted_viewer': self.is_restricted_viewer})
        return result
