'''
Copyright 2022 Airbus SAS
Modifications on 2023/11/23 Copyright 2023 Capgemini

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

from sos_trades_api.server.base_server import study_case_cache

"""
Visualisation Functions
"""


class VisualisationError(Exception):
    """Base StudyCase Exception"""

    def __init__(self, msg=None):
        Exception.__init__(self, msg)

    def __str__(self):
        return self.__class__.__name__ + "(" + Exception.__str__(self) + ")"


def get_execution_sequence_graph_data(study_id):
    """
    Retrieve study case, execution sequence graph data
    """
    study_manager = study_case_cache.get_study_case(study_id, False, False)

    result = study_manager.get_execution_sequence_graph_data()

    return result


def get_n2_diagram_graph_data(study_id: int) -> dict:
    """
    Generate n2 diagram of a loaded study

    Args:
        study_id (int): identifier of the study

    Returns:
        dict: Graph data containing n2 diagram information

    """
    graph = {}
    # Check if study is loaded
    if not study_case_cache.is_study_case_cached(study_id):
        raise VisualisationError("Study case has to be loaded first before requesting for n2 diagram")

    # Get study case manager
    study_case_manager = study_case_cache.get_study_case(study_id, False, False)

    # Get couplings
    try:
        graph = study_case_manager.get_n2_diagram_graph_data()
    except Exception as error:
        raise VisualisationError(str(error))

    return graph


def get_interface_diagram_data(study_id):
    """
    Retrieve study case, interface diagram data
    """
    try:
        study = study_case_cache.get_study_case(study_id, False, False)
        # interface diagram generation
        result = study.get_interface_diagram_graph_data()

        return result
    except Exception as ex:
        raise ex
