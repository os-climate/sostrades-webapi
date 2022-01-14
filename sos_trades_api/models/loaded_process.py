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
        self.process_description = ''
        self.repository_id = repository_id
        self.repository_name = repository_id
        self.repository_description = ''
        self.is_manager = False
        self.is_contributor = False
        self.reference_list = None

    def apply_ontology(self, process_metadata, repository_metadata):

        process_key = f'{self.repository_id}.{self.process_id}'

        if process_metadata is not None and process_key in process_metadata:
            if process_metadata[process_key].get('label', None) is not None:
                self.process_name = process_metadata[process_key]['label']
            if process_metadata[process_key].get('description', None) is not None:
                self.process_description = process_metadata[process_key]['description']

        if repository_metadata is not None and self.repository_id in repository_metadata:
            if repository_metadata[self.repository_id].get('label', None) is not None:
                self.repository_name = repository_metadata[self.repository_id]['label']
            if repository_metadata[self.repository_id].get('description', None) is not None:
                self.repository_description = repository_metadata[self.repository_id]['description']

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'id': self.id,
            'process_id': self.process_id,
            'process_name': self.process_name,
            'process_description': self.process_description,
            'repository_id': self.repository_id,
            'repository_name': self.repository_name,
            'repository_description': self.repository_description,
            'is_manager': self.is_manager,
            'is_contributor': self.is_contributor,
            'reference_list': self.reference_list,
        }
