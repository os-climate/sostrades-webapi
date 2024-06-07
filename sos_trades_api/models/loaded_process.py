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
Class that represent process with ontology information
"""


class LoadedProcess:

    def __init__(self, id, process_id, repository_id):
        self.id = id
        self.process_id = process_id
        self.process_name = process_id
        self.process_description = ""
        self.repository_id = repository_id
        self.repository_name = repository_id
        self.repository_description = ""
        self.is_manager = False
        self.is_contributor = False
        self.reference_list = None
        self.identifier = None
        self.uri = ""
        self.description = ""
        self.category = ""
        self.version = ""
        self.quantity_disciplines_used = 0
        self.discipline_list = None
        self.associated_usecases = None

    def apply_ontology(self, processes_ontology_metadata):

        process_key = f"{self.repository_id}.{self.process_id}"

        ontology_process_request = list(filter(lambda po: po["id"] == process_key, processes_ontology_metadata))

        if len(ontology_process_request) == 1:
            ontology_process = ontology_process_request[0]
            self.deserialize(ontology_process)

    def deserialize(self, json_dict):
        self.identifier = json_dict["id"]
        self.uri = json_dict["uri"]
        self.process_name = json_dict["label"]
        self.description = json_dict["description"]
        self.category = json_dict["category"]
        self.version = json_dict["version"]
        self.repository_name = json_dict["process_repository_label"]
        self.quantity_disciplines_used = json_dict["quantity_disciplines_used"]
        self.discipline_list = json_dict["discipline_list"]
        self.associated_usecases = json_dict["associated_usecases"]

    def serialize(self):
        """
        json serializer for dto purpose
        """
        return {
            "id": self.id,
            "process_id": self.process_id,
            "process_name": self.process_name,
            "process_description": self.process_description,
            "repository_id": self.repository_id,
            "repository_name": self.repository_name,
            "repository_description": self.repository_description,
            "is_manager": self.is_manager,
            "is_contributor": self.is_contributor,
            "reference_list": self.reference_list,
            "identifier": self.identifier,
            "uri": self.uri,
            "description": self.description,
            "category": self.category,
            "version": self.version,
            "quantity_disciplines_used": self.quantity_disciplines_used,
            "discipline_list": self.discipline_list,
            "associated_usecases": self.associated_usecases,
        }
