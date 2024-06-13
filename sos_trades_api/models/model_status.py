'''
Copyright 2022 Airbus SAS
Modifications on 2024/06/07 Copyright 2024 Capgemini
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
Class that represent a model status
"""


class ModelStatus:
    def __init__(self):
        self.id = None
        self.name = ""
        self.definition = ""
        self.type = None
        self.source = None
        self.last_modification_date = None
        self.validated_by = None
        self.validated = None
        self.code_repository = None
        self.processes_using_model = None
        self.processes_using_model_list = None
        self.inputs_parameters_quantity = None
        self.outputs_parameters_quantity = None
        self.icon = None
        self.version = None
        self.category = None

    def serialize(self):
        """Json serializer for dto purpose"""
        return {
            "id": self.id,
            "name": self.name,
            "definition": self.definition,
            "type": self.type,
            "source": self.source,
            "last_modification_date": self.last_modification_date,
            "validated_by": self.validated_by,
            "validated": self.validated,
            "code_repository": self.code_repository,
            "processes_using_model": self.processes_using_model,
            "processes_using_model_list": self.processes_using_model_list,
            "inputs_parameters_quantity": self.inputs_parameters_quantity,
            "outputs_parameters_quantity": self.outputs_parameters_quantity,
            "icon": self.icon,
            "version": self.version,
            "category": self.category,
        }

    def deserialize(self, json_dict):
        self.id = json_dict["id"]
        self.name = json_dict["name"]
        self.definition = json_dict["definition"]
        self.type = json_dict["type"]
        self.source = json_dict["source"]
        self.last_modification_date = json_dict["last_modification_date"]
        self.validated_by = json_dict["validated_by"]
        self.validated = json_dict["validated"]
        self.code_repository = json_dict["code_repository"]
        self.processes_using_model = json_dict["processes_using_model"]
        self.processes_using_model_list = json_dict["processes_using_model_list"]
        self.inputs_parameters_quantity = json_dict["inputs_parameters_quantity"]
        self.outputs_parameters_quantity = json_dict["outputs_parameters_quantity"]
        self.icon = json_dict["icon"]
        self.version = json_dict["version"]
        self.category = json_dict["category"]
