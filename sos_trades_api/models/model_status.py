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
Class that represent a model status
"""


class ModelStatus:

    def __init__(self):
        self.id = None
        self.name = ''
        self.description = ''
        self.model_type = None
        self.source = None
        self.delivered = False
        self.implemented = False
        self.last_publication_date = None
        self.validator = None
        self.validated = None
        self.discipline = None
        self.processes_using_model = None
        self.processes_using_model_list = None
        self.inputs_parameters_quantity = None
        self.outputs_parameters_quantity = None

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'model_type': self.model_type,
            'source': self.source,
            'delivered': self.delivered,
            'implemented': self.implemented,
            'last_publication_date': self.last_publication_date,
            'validator': self.validator,
            'validated': self.validated,
            'discipline': self.discipline,
            'processes_using_model': self.processes_using_model,
            'processes_using_model_list': self.processes_using_model_list,
            'inputs_parameters_quantity': self.inputs_parameters_quantity,
            'outputs_parameters_quantity': self.outputs_parameters_quantity,
        }

    def deserialize(self, json_dict):
        self.id = json_dict['id']
        self.name = json_dict['name']
        self.description = json_dict['description']
        self.model_type = json_dict['model_type']
        self.source = json_dict['source']
        self.delivered = json_dict['delivered']
        self.implemented = json_dict['implemented']
        self.last_publication_date = json_dict['last_publication_date']
        self.validator = json_dict['validator']
        self.validated = json_dict['validated']
        self.discipline = json_dict['discipline']
        self.processes_using_model = json_dict['processes_using_model']
        self.processes_using_model_list = json_dict['processes_using_model_list']
        self.inputs_parameters_quantity = json_dict['inputs_parameters_quantity']
        self.outputs_parameters_quantity = json_dict['outputs_parameters_quantity']