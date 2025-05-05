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

from dataclasses import dataclass
from typing import Dict


@dataclass
class OntologyDataNames:
    parameter_usages: set
    disciplines: set




def flatten_tree_node(tree_node: Dict) -> Dict:
    """
    Recursively flatten a loaded study tree node

    :param tree_node: tree node with 'data' and 'children' keys
    :type: dict

    :return: {disc: disc_values} flatten tree node
    :rtype: dict
    """
    flattened_tree_node = tree_node.get("data", {})

    for child in tree_node.get("children", []):
        flattened_tree_node.update(flatten_tree_node(child))

    return flattened_tree_node

def get_treenode_ontology_data(tree_node: Dict)->OntologyDataNames:

    #perpare ontology dict
    ontology_data = OntologyDataNames(set(),set())
    
    ontology_data.disciplines.update(tree_node.get('models_full_path_list', []))
    
    for data_name, data in tree_node.get('data',{}).items():
        key = data.get('variable_key', None)
        if (key is not None):
            ontology_data.parameter_usages.add(key)

    for disc_name, discipline in tree_node.get('data_management_disciplines', {}).items():
        print(discipline)
        for name, data in discipline.get('disciplinary_inputs', {}).items():
            key = data.get('variable_key', None)
            if (key is not None):
                ontology_data.parameter_usages.add(key)
        for name, data in discipline.get('disciplinary_outputs', {}).items():
            key = data.get('variable_key', None)
            if (key is not None):
                ontology_data.parameter_usages.add(key)


    for child in tree_node.get('children', {}):
        child_ontology_data = get_treenode_ontology_data(child)
        ontology_data.parameter_usages.update(child_ontology_data.parameter_usages)
        ontology_data.disciplines.update(child_ontology_data.disciplines)
    
    return ontology_data


                
