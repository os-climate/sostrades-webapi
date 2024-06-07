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
from sos_trades_api.controllers.sostrades_data.ontology_controller import (
    generate_n2_matrix,
)
from sos_trades_api.server.base_server import study_case_cache
from sos_trades_api.tools.visualisation.execution_workflow_graph import (
    SoSExecutionWorkflow,
)
from sos_trades_api.tools.visualisation.interface_diagram import (
    InterfaceDiagramGenerator,
)


class VisualisationError(Exception):
    """Base StudyCase Exception"""

    def __init__(self, msg=None):
        Exception.__init__(self, msg)

    def __str__(self):
        return self.__class__.__name__ + '(' + Exception.__str__(self) + ')'


def get_execution_sequence_graph_data(study_id):
    """
    Retrieve study case, execution sequence graph data
    """
    study_manager = study_case_cache.get_study_case(study_id, False, False)

    GEMS_graph = study_manager.execution_engine.root_process.coupling_structure.graph

    # execution workflow generation
    execution_workflow = SoSExecutionWorkflow(GEMS_graph)
    execution_workflow.get_execution_workflow_graph()

    result = execution_workflow.create_result()

    return result


def get_n2_diagram_graph_data(study_id):
    """
    Generate n2 diagram of a loaded study
    :param study_id: id of the study
    :type study_id: integer

    :return: dictionary
    """

    if not study_case_cache.is_study_case_cached(study_id):
        raise VisualisationError('Study case has to be loaded first before requesting for n2 diagram')

    study_case_manager = study_case_cache.get_study_case(study_id, False, False)

    return generate_n2_matrix(study_case_manager)

def get_interface_diagram_data(study_id):
    """
    Retrieve study case, interface diagram data
    """
    study = study_case_cache.get_study_case(study_id, False, False)

    # interface diagram generation
    interface_diagram= InterfaceDiagramGenerator(study)
    result =interface_diagram.generate_interface_diagram_data()

    return result