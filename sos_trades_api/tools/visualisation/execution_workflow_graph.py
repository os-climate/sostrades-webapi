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
tooling to generate D3 js data structure for N2 matrix purpose
"""

from sos_trades_core.api import get_sos_logger
import time
from graphviz import Digraph


class SoSExecutionWorkflow():
    """
    Class to construct an execution workflow from GEMS execution sequence
    """

    def __init__(self, GEMS_graph=None):
        """
        Constructor
        """
        self.GEMS_graph = GEMS_graph
        self.nodes_dict = {}
        self.links_dict = {}
        self.unique_disc = set()
        self.unique_parameters = set()
        self.step_count = 0
        self.mda_count = 0
        self.output_node_count = 0
        self.result = {}

    def get_execution_workflow_graph(self):

        start_time = time.time()
        logger = get_sos_logger('SoS')
        self.construct_execution_workflow_graph(
            GEMS_graph=self.GEMS_graph,
            level=0,
            parentId=None)

        self.create_study_output_links()

        self.create_cluster_links()

        self.create_dot_graph()

        # # outputs of the last nodes
        # last_tasks = self.GEMS_graph.execution_sequence[-1]
        # for i, last_task in enumerate(last_tasks):
        #     last_taskind = last_task[0]
        #     i_str = "-" + str(i)
        #     last_outputs = self.GEMS_graph.disciplines[
        #         last_taskind].get_output_data_names()
        #     last_outputs = [n.split('.')[-1] for n in last_outputs]  # PBX
        #     if last_outputs != []:
        #         # create an edge to an invisible node
        #         dot.node(i_str, style='invis', shape="point")
        #         # label = ','.join(last_outputs)
        #         label = '\n'.join(last_outputs)
        #         dot.edge(str(last_task), i_str, label=label)
        #         # dot.edge(str(last_task), i_str)

        # last_tasks = self.GEMS_graph.execution_sequence[-1]
        # for k, last_task in enumerate(last_tasks):
        #     last_taskind = last_task[0]
        #     i_str = "-" + str(k)
        #     disc = self.GEMS_graph.disciplines[last_taskind]
        #     last_outputs = disc.get_output_data_names()
        #     if last_outputs != []:
        #         # create an edge to an invisible node
        #         dot_full.node(i_str, style='invis', shape="point")
        #         label = '\n'.join(last_outputs)
        #         dot_full.edge(disc_dict[disc], i_str, label=label)

        logger.info(
            f'Execution Workflow data generated in {time.time() - start_time} seconds')

        return ''

    def construct_execution_workflow_graph(self, GEMS_graph, level, parentId):
        root_disc_id = []
        # create initial links between leaf nodes
        self.get_initial_links(
            GEMS_graph=GEMS_graph)

        # go through the sequence to create nodes
        for parallel_tasks in GEMS_graph.get_execution_sequence():
            if len(parallel_tasks) == 1:
                # it is a sequence composed of only one discipline or MDA
                # no need to create a dedicated node for it

                if len(parallel_tasks[0]) == 1:
                    # it is a sequence step composed of only one discipline
                    disc = parallel_tasks[0][0]

                    disc_info = self.create_mono_disc_node(
                        disc=disc,
                        level=level,
                        parentId=parentId,
                        GEMS_graph=GEMS_graph)

                else:
                    # it is a sequence composed on one MDA
                    disc_info = self.create_MDA_node(
                        cycle_disc=parallel_tasks[0],
                        level=level,
                        parentId=parentId,
                        GEMS_graph=GEMS_graph)

            else:
                # it is a sequence composed of at least several disciplines
                disc_info = self.create_parallel_node(
                    parallel_tasks=parallel_tasks,
                    level=level,
                    parentId=parentId,
                    GEMS_graph=GEMS_graph)

            root_disc_id.append(disc_info['id'])
        return root_disc_id

    def create_mono_disc_node(self, disc, level, parentId, GEMS_graph):
        disc_node_info = {}
        disc_node_info['id'] = disc.disc_id
        disc_node_info['type'] = 'DisciplineNode'
        disc_node_info['disc_name'] = type(disc).__name__

        disc_name = disc.get_disc_full_name()
        # remove study name from full name
        disc_name = '.'.join(disc_name.split('.')[1:])
        disc_node_info['label'] = disc_name
        disc_node_info['status'] = disc.status
        disc_node_info['level'] = level
        disc_node_info['parent'] = parentId
        disc_node_info['path'] = disc.__module__

        # add discipline class to unique list. useful to retrieve ontology information only once
        if disc_node_info['path'] not in self.unique_disc:
            self.unique_disc.add(disc_node_info['path'])

        children = []
        # recursivity
        if hasattr(disc, 'disciplines'):
            if type(disc).__name__ == 'SoSCoupling':
                # it is a Coupling
                disc_node_info['type'] = 'CouplingNode'
                sub_GEMS_graph = disc.coupling_structure.graph

                # add missing links between graphs
                self.add_links_from_sub_nodes_to_current_graph(
                    GEMS_graph=GEMS_graph,
                    coupling_disc_id=disc.disc_id,
                    sub_GEMS_graph=sub_GEMS_graph)

                # construct workflow for sub graph
                root_disc_id_list = self.construct_execution_workflow_graph(
                    GEMS_graph=sub_GEMS_graph,
                    level=level+1,
                    parentId=disc.disc_id)

                children = root_disc_id_list

            if type(disc).__name__ == 'SoSOptimScenario':
                for disc_child in disc.disciplines:
                    children.append(disc_child.disc_id)
                    # it is an optim scenario
                    self.create_mono_disc_node(
                        disc=disc_child,
                        level=level+1,
                        parentId=disc.disc_id,
                        GEMS_graph=GEMS_graph)

        disc_node_info['children'] = children
        self.nodes_dict[disc.disc_id] = disc_node_info

        return disc_node_info

    def add_links_from_sub_nodes_to_current_graph(self, GEMS_graph, coupling_disc_id, sub_GEMS_graph):
        # retrieve links that we will need to recreate
        coupling_out_links = []
        couplings = GEMS_graph.get_disciplines_couplings()
        for (disc_from, disc_to, edge_parameters_list) in couplings:
            disc_from_id = disc_from.disc_id
            disc_to_id = disc_to.disc_id
            # the discipline has been found and all out links need to be re-created
            if disc_from_id == coupling_disc_id:
                link = {
                    'from': disc_from_id,
                    'to': disc_to_id,
                    'parameters': edge_parameters_list,
                }
                coupling_out_links.append(link)

        # finding in links
        coupling_in_links = []
        for (disc_from, disc_to, edge_parameters_list) in couplings:
            disc_from_id = disc_from.disc_id
            disc_to_id = disc_to.disc_id
            if disc_to_id == coupling_disc_id:
                # the discipline has been found and all in links need to be re-created
                link = {
                    'from': disc_from_id,
                    'to': disc_to_id,
                    'parameters': edge_parameters_list,
                }
                coupling_in_links.append(link)

        # creating a dictionary of parameter and emitter discipline id
        parameter_emitter_disc = {}
        for disc in sub_GEMS_graph.disciplines:
            out_parameters = disc.get_output_data_names()
            for out_param in out_parameters:
                parameter_emitter_disc[out_param] = disc.disc_id

        # starting to re-create out-links from sub nodes
        for out_link in coupling_out_links:
            # for each parameter exchanged, we need to find which sub_nodes is creating it as output
            new_link = {}
            for out_param in out_link['parameters']:
                emitter_disc = parameter_emitter_disc[out_param]
                param_simple_name = out_param.split('.')[-1]
                if emitter_disc in new_link:
                    new_link[emitter_disc].append(param_simple_name)
                else:
                    new_link[emitter_disc] = [param_simple_name]

            for emitter_disc, parameters_list in new_link.items():
                link_id = f'{emitter_disc}->{out_link["to"]}'
                if link_id not in self.links_dict:
                    link = {
                        'id': link_id,
                        'from': emitter_disc,
                        'to': out_link["to"],
                        'parameters': {p for p in parameters_list},
                        'type': 'couplingLink'
                    }
                    self.links_dict[link_id] = link

        # creating a dictionary of parameter and emitter discipline id
        parameter_input_disc = {}
        for disc in sub_GEMS_graph.disciplines:
            in_parameters = disc.get_input_data_names()
            for in_param in in_parameters:
                if in_param in parameter_input_disc:
                    parameter_input_disc[in_param].append(disc.disc_id)
                else:
                    parameter_input_disc[in_param] = [disc.disc_id]

        # finaly create in-links to sub nodes
        for in_link in coupling_in_links:
            # for each parameter exchanged, we need to find which sub_nodes is receiving it as input
            new_link = {}
            for in_param in in_link['parameters']:
                receiver_discs = parameter_input_disc[in_param]
                param_simple_name = in_param.split('.')[-1]
                for receiver_disc in receiver_discs:
                    if receiver_disc in new_link:
                        new_link[receiver_disc].append(param_simple_name)
                    else:
                        new_link[receiver_disc] = [param_simple_name]

            for receiver_disc, parameters_list in new_link.items():
                link_id = f'{in_link["from"]}->{receiver_disc}'
                if link_id not in self.links_dict:
                    link = {
                        'id': link_id,
                        'from': in_link["from"],
                        'to': receiver_disc,
                        'parameters': {p for p in parameters_list},
                        'type': 'couplingLink'
                    }
                    self.links_dict[link_id] = link

    def create_MDA_node(self, cycle_disc, level, parentId, GEMS_graph):

        self.mda_count += 1
        mda_node_id = f'cycleDisc{self.mda_count}'
        mda_node_info = dict(
            id=mda_node_id,
            type='MDANode',
            disc_name='',
            label=f'MDA {self.mda_count}',
            status='',
            level=level,
            parent=parentId,
            children=[],
            is_MDA=True,
        )

        for disc in cycle_disc:
            mda_node_info['children'].append(disc.disc_id)

            self.create_mono_disc_node(
                disc=disc,
                level=level+1,
                parentId=mda_node_id,
                GEMS_graph=GEMS_graph)

        self.nodes_dict[mda_node_id] = mda_node_info
        return mda_node_info

    def create_parallel_node(self, parallel_tasks, level, parentId, GEMS_graph):
        self.step_count += 1
        parallel_node_id = f'parallelDiscs{self.step_count}'
        parallel_node_info = dict(
            id=parallel_node_id,
            type='ParallelNode',
            label=f'Parallel Nodes {self.step_count}',
            status='',
            disc_name='',
            level=level,
            parent=parentId,
            children=[],
            is_MDA=False,
        )
        for cycle_disc in parallel_tasks:
            if len(cycle_disc) > 1:
                MDAnode = self.create_MDA_node(
                    cycle_disc=cycle_disc,
                    level=level+1,
                    parentId=parallel_node_id,
                    GEMS_graph=GEMS_graph)

                parallel_node_info['children'].append(MDAnode['id'])
            else:
                disc = cycle_disc[0]
                node = self.create_mono_disc_node(
                    disc=disc,
                    level=level+1,
                    parentId=parallel_node_id,
                    GEMS_graph=GEMS_graph)

                parallel_node_info['children'].append(node['id'])

        self.nodes_dict[parallel_node_id] = parallel_node_info
        return parallel_node_info

    def get_initial_links(self, GEMS_graph):
        couplings = GEMS_graph.get_disciplines_couplings()
        for (disc_from, disc_to, edge_parameters_list) in couplings:
            disc_from_id = disc_from.disc_id
            disc_to_id = disc_to.disc_id
            link_id = f'{disc_from_id}->{disc_to_id}'
            if link_id not in self.links_dict:
                link = {
                    'id': link_id,
                    'from': disc_from_id,
                    'to': disc_to_id,
                    'parameters': set(),
                    'type': 'couplingLink'
                }
                self.links_dict[link_id] = link
                for output_param in edge_parameters_list:
                    param_name = output_param.split('.')[-1]
                    self.links_dict[link_id]['parameters'].add(param_name)
                    if param_name not in self.unique_parameters:
                        self.unique_parameters.add(param_name)

    # def get_initial_links_old(self, GEMS_graph):
    #     for disc_from in GEMS_graph.initial_edges:
    #         disc_from_id = disc_from.disc_id
    #         for disc_to in GEMS_graph.initial_edges[disc_from]:
    #             disc_to_id = disc_to.disc_id
    #             link_id = f'{disc_from_id}->{disc_to_id}'
    #             if link_id not in self.links_dict:
    #                 link = {
    #                     'id': link_id,
    #                     'from': disc_from_id,
    #                     'to': disc_to_id,
    #                     'parameters': set(),
    #                     'type': 'couplingLink'
    #                 }
    #                 self.links_dict[link_id] = link
    #             outputs_parameters = GEMS_graph.initial_edges[disc_from][disc_to]
    #             for output_param in outputs_parameters:
    #                 param_name = output_param.split('.')[-1]
    #                 self.links_dict[link_id]['parameters'].add(param_name)
    #                 if param_name not in self.unique_parameters:
    #                     self.unique_parameters.add(param_name)

    def create_study_output_links(self):
        # retrieve last disciplines run
        last_tasks = self.GEMS_graph.get_execution_sequence()[-1]
        for last_task in last_tasks:
            last_disc = last_task[0]
            last_disc_id = last_disc.disc_id
            last_outputs = last_disc.get_output_data_names()
            last_outputs = [n.split('.')[-1] for n in last_outputs]  # PBX
            if last_outputs != []:
                # create an invisible node
                self.output_node_count += 1
                output_node_id = f'outputNode{self.output_node_count}'
                output_node_info = dict(
                    id=output_node_id,
                    type='OutputNode',
                    disc_name='',
                    label=f'Output {self.output_node_count}',
                    status='',
                    level='',
                    parent=None,
                    children=[],
                    is_MDA=False,
                )
                self.nodes_dict[output_node_id] = output_node_info

                # create an edge to an invisible node
                link_id = f'{last_disc_id}->{output_node_id}'
                parameters = set()
                for p in last_outputs:
                    param_name = p.split('.')[-1]
                    parameters.add(param_name)
                    if param_name not in self.unique_parameters:
                        self.unique_parameters.add(param_name)
                if link_id not in self.links_dict:
                    link = {
                        'id': link_id,
                        'from': last_disc_id,
                        'to': output_node_id,
                        'parameters': parameters,
                        'type': 'outputLink'
                    }
                    self.links_dict[link_id] = link

    def create_cluster_links(self):
        # create in and out links from / to parents of disc nodes
        for node_id, node in self.nodes_dict.items():
            node_with_links = self.create_from_to_links_with_parents(node)
            self.nodes_dict[node_id] = node_with_links

        # create links between group nodes
        groupNodeList = {disc_id: disc for (disc_id, disc) in self.nodes_dict.items() if (
            disc['type'] == 'ParallelNode' or disc['type'] == 'MDANode' or disc['type'] == 'CouplingNode')}
        for groupNodeId, groupNode in groupNodeList.items():
            groupNode_with_links = self.create_from_to_links_with_parents(
                groupNode)
            self.nodes_dict[groupNodeId] = groupNode_with_links

    def create_from_to_links_with_parents(self, node):
        node['hasLinks'] = False
        node['inLinks'] = []
        node['outLinks'] = []

        inLinksDict = {link_id: link for (
            link_id, link) in self.links_dict.items() if link['to'] == node['id']}
        outLinksDict = {link_id: link for (
            link_id, link) in self.links_dict.items() if link['from'] == node['id']}

        inLinksList = list(inLinksDict.keys())
        outLinksList = list(outLinksDict.keys())

        if len(inLinksList) > 0 or len(outLinksList) > 0:
            node['hasLinks'] = True

        # create out links to parent group nodes
        for outlink in outLinksDict.values():
            discToId = outlink['to']
            discTo = self.nodes_dict[discToId]
            parentId = discTo['parent']
            while parentId is not None:
                if outlink["from"] != parentId:
                    link_id = f'{outlink["from"]}->{parentId}'
                    if link_id not in self.links_dict:
                        # create links to parent node
                        link = {
                            'id': link_id,
                            'from': outlink["from"],
                            'to': parentId,
                            'parameters': outlink['parameters'],
                            'type': outlink['type']
                        }
                        self.links_dict[link_id] = link
                        outLinksList.append(link_id)
                    else:
                        parameters = self.links_dict[link_id]['parameters'].union(
                            outlink['parameters'])
                        self.links_dict[link_id]['parameters'] = parameters
                discToParent = self.nodes_dict[parentId]
                parentId = discToParent['parent']

        # create in links to parent group nodes
        for inlink in inLinksDict.values():
            discFromId = inlink['from']
            discFrom = self.nodes_dict[discFromId]
            parentId = discFrom['parent']
            while parentId is not None:
                if inlink["to"] != parentId:
                    link_id = f'{parentId}->{inlink["to"]}'
                    if link_id not in self.links_dict:
                        # create links to parent node
                        link = {
                            'id': link_id,
                            'from': parentId,
                            'to': inlink["to"],
                            'parameters': inlink['parameters'],
                            'type': inlink['type'],
                        }
                        self.links_dict[link_id] = link
                        inLinksList.append(link_id)
                    else:
                        parameters = self.links_dict[link_id]['parameters'].union(
                            inlink['parameters'])
                        self.links_dict[link_id]['parameters'] = parameters
                discFromParent = self.nodes_dict[parentId]
                parentId = discFromParent['parent']

        node['inLinks'] = inLinksList
        node['outLinks'] = outLinksList

        return node

    def create_dot_graph(self):
        dot = Digraph(comment='Dependency graph', format='svg',
                      graph_attr={'rankdir': 'LR'})
        drawn_nodes = set()

        for nodeId, node in self.nodes_dict.items():
            if node['hasLinks'] == True and node['level'] == 1:
                dot.node(name=str(nodeId), label='\n'.join(
                    [node['label'], node['type']]), tooltip=nodeId)
                drawn_nodes.add(nodeId)

        # filter links on drawn nodes
        filtered_links = {linkId: link for (linkId, link) in self.links_dict.items() if (
            link['from'] in drawn_nodes and link['to'] in drawn_nodes)}
        for link in filtered_links.values():
            dot.edge(str(link['from']), str(link['to']), label='')
        return dot

    def create_result(self):
        # convert set to list to avoid JSON parsing error
        for linkId, link in self.links_dict.items():
            parameter_set = link['parameters']
            parameter_list = list(parameter_set)
            self.links_dict[linkId]['parameters'] = parameter_list
        self.result = {
            'nodes_list': list(self.nodes_dict.values()),
            'links_list': list(self.links_dict.values()),
            'dotString': self.create_dot_graph().source
        }
        return self.result
