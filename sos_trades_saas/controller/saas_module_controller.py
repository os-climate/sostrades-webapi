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


def filter_discipline(discipline: dict) -> dict:
    """
        Filter one discipline.
        :type: dict
        :params: discipline, represent a 'discipline'.
        :rtype: dict
        :return: Sub discipline .
    """
    keys = ["var_name", "type", "unit", "value", "visibility", "optional"]
    return {key: value for key, value in discipline.items() if key in keys}


def filter_tree_node_data(tree_node: dict) -> dict:
    """
    Filter all editable inputs or numerical parameters from 'tree_node_data'.
    :type: dict
    :params: tree_node, represent the 'treenode'.
    :rtype: dict
    :return: dictionary of filtered discipline .
    """
    return {key: filter_discipline(value) for key, value in tree_node.get("data").items() if value.get("numerical") or
            (value.get("editable") and value.get("io_type") == "in")}


def filter_children_data(tree_node: dict) -> list:
    """
    Filter numerical or input parameters from 'tree_node'.
    :type: dict
    :params: tree_node, represent the 'treenode'.
    :rtype: dict
    :return: dict of filtered dictionary.
    """
    filtered_children = []
    for child in tree_node.get("children"):
        filtered_child = {
            "data": filter_tree_node_data(child)
        }
        if len(child.get("children", [])) > 0:
            filtered_child.update({
                "children": filter_children_data(child)
            })
        filtered_children.append(filtered_child)
    return filtered_children
