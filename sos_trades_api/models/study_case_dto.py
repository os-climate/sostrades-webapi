'''
Copyright 2022 Airbus SAS
Modifications on 2024/03/05-2024/03/22 Copyright 2024 Capgemini

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
from sos_trades_api.models.database_models import (
    AccessRights,
    Group,
    StudyCaseAccessGroup,
)

"""
Class that represent a study case data transfert object with group information
"""


class StudyCaseDto:

    def __init__(self, study_case_instance=None, owner_group=None):
        """
        Initialize DTO using a study case instance

        :params: study_case_instance, instance of database study case
        :type: sostrades_webapi.models.database_models.StudyCase
        """
        self.id = None
        self.name = ""
        self.process = ""
        self.repository = ""
        self.process_display_name = ""
        self.repository_display_name = ""
        self.creation_date = ""
        self.modification_date = ""
        self.execution_status = ""
        self.creation_status = ""
        self.study_type = ""
        self.group_name = ""
        self.group_id = None
        self.group_confidential = ""
        self.is_reference_running = False
        self.regeneration_id = None
        self.regeneration_status = None
        self.is_manager = False
        self.is_contributor = False
        self.is_commenter = False
        self.is_restricted_viewer = False
        self.disabled = False
        self.is_favorite = False
        self.current_execution_id = None
        self.is_last_study_opened = False
        self.opening_date = ""
        self.error = ""
        self.study_pod_flavor = None
        self.execution_pod_flavor = None
        self.generation_pod_flavor = None

        if study_case_instance is not None:
            self.id = study_case_instance.id
            self.name = study_case_instance.name
            self.process = study_case_instance.process
            self.repository = study_case_instance.repository
            self.creation_date = study_case_instance.creation_date
            self.current_execution_id = study_case_instance.current_execution_id
            self.creation_status = study_case_instance.creation_status
            self.error = study_case_instance.error
            self.modification_date = study_case_instance.modification_date
            self.process_display_name = study_case_instance.process
            self.repository_display_name = study_case_instance.repository
            self.disabled = study_case_instance.disabled
            self.study_type = "Study"
            self.study_pod_flavor = study_case_instance.study_pod_flavor
            self.execution_pod_flavor = study_case_instance.execution_pod_flavor

            # Retrieve group owner
            if owner_group is None:
                owner_right = AccessRights.query.filter(
                    AccessRights.access_right == AccessRights.OWNER).first()
                if owner_right is not None:
                    owner_group = Group.query.join(StudyCaseAccessGroup)\
                        .filter(StudyCaseAccessGroup.study_case_id == study_case_instance.id)\
                        .filter(StudyCaseAccessGroup.right_id == owner_right.id)\
                        .first()

            if owner_group is not None:
                self.group_name = owner_group.name
                self.group_id = owner_group.id
                self.group_confidential = owner_group.confidential

    def __eq__(self, other):

        for attribute_name in self.__dict__.keys():
            if not self.__dict__[attribute_name] == other.__dict__[attribute_name]:
                print(f"Check object equality {self.id}/{other.id}")
                print(f"Attribute {attribute_name} is different {self.__dict__[attribute_name]}/{other.__dict__[attribute_name]}")
                return False
        return True

    def apply_ontology(self, process_metadata, repository_metadata):

        process_key = f"{self.repository}.{self.process}"

        if process_metadata is not None and process_key in process_metadata:
            if process_metadata[process_key].get("label", None) is not None:
                self.process_display_name = process_metadata[process_key]["label"]

        if repository_metadata is not None and self.repository in repository_metadata:
            if repository_metadata[self.repository].get("label", None) is not None:
                self.repository_display_name = repository_metadata[self.repository]["label"]

    def serialize(self):
        """
        json serializer for dto purpose
        """
        result = {}
        result.update({"id": self.id})
        result.update({"name": self.name})
        result.update({"process": self.process})
        result.update({"repository": self.repository})
        result.update({"process_display_name": self.process_display_name})
        result.update({"repository_display_name": self.repository_display_name})
        result.update({"creation_date": self.creation_date})
        result.update({"modification_date": self.modification_date})
        result.update({"execution_status": self.execution_status})
        result.update({"creation_status": self.creation_status})
        result.update({"study_type": self.study_type})
        result.update({"group_name": self.group_name})
        result.update({"group_id": self.group_id})
        result.update({"group_confidential": self.group_confidential})
        result.update({"is_reference_running": self.is_reference_running})
        result.update({"regeneration_id": self.regeneration_id})
        result.update({"regeneration_status": self.regeneration_status})
        result.update({"is_manager": self.is_manager})
        result.update({"is_contributor": self.is_contributor})
        result.update({"is_commenter": self.is_commenter})
        result.update({"is_restricted_viewer": self.is_restricted_viewer})
        result.update({"is_favorite": self.is_favorite})
        result.update({"is_last_study_opened": self.is_last_study_opened})
        result.update({"opening_date": self.opening_date})
        result.update({"error": self.error})
        result.update({"study_pod_flavor": self.study_pod_flavor})
        result.update({"execution_pod_flavor": self.execution_pod_flavor})
        result.update({"generation_pod_flavor": self.generation_pod_flavor})

        return result

