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

from typing import Dict


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
