'''
Copyright 2022 Airbus SAS
Modifications on 2023/05/12-2023/11/03 Copyright 2023 Capgemini

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

import logging
import time

from graphviz import Digraph


class SoSExecutionWorkflow:
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
        logger = logging.getLogger(__name__)
        self.construct_execution_workflow_graph(
            GEMS_graph=self.GEMS_graph, level=0, parentId=None
        )

        # test to simplify workflow by removing scatter data
        # not yet operational
        # self.generate_scatter_data_mapping()

        self.create_study_output_links()

        self.create_cluster_links()

        self.create_dot_graph()

        logger.info(
            f'Execution Workflow data generated in {time.time() - start_time} seconds'
        )

        return ''

    def construct_execution_workflow_graph(self, GEMS_graph, level, parentId):
        root_disc_id = []
        # create initial links between leaf nodes
        self.get_initial_links(GEMS_graph=GEMS_graph)

        # go through the sequence to create nodes
        for parallel_tasks in GEMS_graph.get_execution_sequence():
            if len(parallel_tasks) == 1:
                # it is a sequence composed of only one discipline or MDA
                # no need to create a dedicated node for it

                if len(parallel_tasks[0]) == 1:
                    # it is a sequence step composed of only one discipline
                    disc = parallel_tasks[0][0]

                    disc_info = self.create_mono_disc_node(
                        disc=disc, level=level, parentId=parentId, GEMS_graph=GEMS_graph
                    )

                else:
                    # it is a sequence composed on one MDA
                    disc_info = self.create_MDA_node(
                        cycle_disc=parallel_tasks[0],
                        level=level,
                        parentId=parentId,
                        GEMS_graph=GEMS_graph,
                    )

            else:
                # it is a sequence composed of at least several disciplines
                disc_info = self.create_parallel_node(
                    parallel_tasks=parallel_tasks,
                    level=level,
                    parentId=parentId,
                    GEMS_graph=GEMS_graph,
                )

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
        disc_node_info['path'] = disc.get_module()

        # add discipline class to unique list. useful to retrieve ontology
        # information only once
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
                    sub_GEMS_graph=sub_GEMS_graph,
                )

                # construct workflow for sub graph
                root_disc_id_list = self.construct_execution_workflow_graph(
                    GEMS_graph=sub_GEMS_graph, level=level + 1, parentId=disc.disc_id
                )

                children = root_disc_id_list

            if type(disc).__name__ == 'SoSOptimScenario':
                for disc_child in disc.disciplines:
                    children.append(disc_child.disc_id)
                    # it is an optim scenario
                    self.create_mono_disc_node(
                        disc=disc_child,
                        level=level + 1,
                        parentId=disc.disc_id,
                        GEMS_graph=GEMS_graph,
                    )
        elif hasattr(disc, 'sos_disciplines'):
            if len(disc.sos_disciplines) == 1:
                # we are probably in the case of an SoSEval equivalent.
                # we need to retrieve sub coupling structure
                sub_disc = disc.sos_disciplines[0]
                disc_node_info['type'] = 'CouplingNode'
                sub_GEMS_graph = sub_disc.coupling_structure.graph

                # add missing links between graphs
                self.add_links_from_sub_nodes_to_current_graph(
                    GEMS_graph=GEMS_graph,
                    coupling_disc_id=disc.disc_id,
                    sub_GEMS_graph=sub_GEMS_graph,
                )

                # construct workflow for sub graph
                root_disc_id_list = self.construct_execution_workflow_graph(
                    GEMS_graph=sub_GEMS_graph, level=level + 1, parentId=disc.disc_id
                )

                children = root_disc_id_list
            elif len(disc.sos_disciplines) > 1:
                raise Exception('What do we do?')

        disc_node_info['children'] = children
        self.nodes_dict[disc.disc_id] = disc_node_info

        return disc_node_info

    def add_links_from_sub_nodes_to_current_graph(
        self, GEMS_graph, coupling_disc_id, sub_GEMS_graph
    ):
        # retrieve links that we will need to recreate
        coupling_out_links = []
        couplings = GEMS_graph.get_disciplines_couplings()
        for (disc_from, disc_to, edge_parameters_list) in couplings:
            disc_from_id = disc_from.disc_id
            disc_to_id = disc_to.disc_id
            # the discipline has been found and all out links need to be
            # re-created
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
                # the discipline has been found and all in links need to be
                # re-created
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
            # for each parameter exchanged, we need to find which sub_nodes is
            # creating it as output
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
                        'type': 'couplingLink',
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
            # for each parameter exchanged, we need to find which sub_nodes is
            # receiving it as input
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
                        'type': 'couplingLink',
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
                disc=disc, level=level + 1, parentId=mda_node_id, GEMS_graph=GEMS_graph
            )

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
                    level=level + 1,
                    parentId=parallel_node_id,
                    GEMS_graph=GEMS_graph,
                )

                parallel_node_info['children'].append(MDAnode['id'])
            else:
                disc = cycle_disc[0]
                node = self.create_mono_disc_node(
                    disc=disc,
                    level=level + 1,
                    parentId=parallel_node_id,
                    GEMS_graph=GEMS_graph,
                )

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
                    'type': 'couplingLink',
                }
                self.links_dict[link_id] = link
                for output_param in edge_parameters_list:
                    # param_name = output_param.split('.')[-1]
                    output_param_data = disc_from.ee.dm.get_data(output_param)
                    param_usage_name = f'{disc_from.get_module()}_{output_param_data.get("io_type","")}put_{output_param_data.get("var_name","")}'
                    self.links_dict[link_id]['parameters'].add(
                        param_usage_name)
                    self.unique_parameters.add(param_usage_name)

    def create_study_output_links(self):
        # retrieve last disciplines run
        last_tasks = self.GEMS_graph.get_execution_sequence()[-1]
        for last_task in last_tasks:
            last_disc = last_task[0]
            last_disc_id = last_disc.disc_id
            last_outputs = last_disc.get_output_data_names()
            # last_outputs = [n.split('.')[-1] for n in last_outputs]  # PBX
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
                for output_param in last_outputs:
                    # param_name = p.split('.')[-1]
                    output_param_data = last_disc.ee.dm.get_data(output_param)
                    param_usage_name = f'{last_disc.get_module()}_{output_param_data.get("io_type","")}put_{output_param_data.get("var_name","")}'
                    parameters.add(param_usage_name)
                    self.unique_parameters.add(param_usage_name)
                if link_id not in self.links_dict:
                    link = {
                        'id': link_id,
                        'from': last_disc_id,
                        'to': output_node_id,
                        'parameters': parameters,
                        'type': 'outputLink',
                    }
                    self.links_dict[link_id] = link

    def create_cluster_links(self):
        # create in and out links from / to parents of disc nodes
        for node_id, node in self.nodes_dict.items():
            node_with_links = self.create_from_to_links_with_parents(node)
            self.nodes_dict[node_id] = node_with_links

        # create links between group nodes
        groupNodeList = {
            disc_id: disc
            for (disc_id, disc) in self.nodes_dict.items()
            if (
                disc['type'] == 'ParallelNode'
                or disc['type'] == 'MDANode'
                or disc['type'] == 'CouplingNode'
            )
        }
        for groupNodeId, groupNode in groupNodeList.items():
            groupNode_with_links = self.create_from_to_links_with_parents(
                groupNode)
            self.nodes_dict[groupNodeId] = groupNode_with_links

    def create_from_to_links_with_parents(self, node):
        node['hasLinks'] = False
        node['inLinks'] = []
        node['outLinks'] = []

        inLinksDict = {
            link_id: link
            for (link_id, link) in self.links_dict.items()
            if link['to'] == node['id']
        }
        outLinksDict = {
            link_id: link
            for (link_id, link) in self.links_dict.items()
            if link['from'] == node['id']
        }

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
                            'type': outlink['type'],
                        }
                        self.links_dict[link_id] = link
                        outLinksList.append(link_id)
                    else:
                        parameters = self.links_dict[link_id]['parameters'].union(
                            outlink['parameters']
                        )
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
                            inlink['parameters']
                        )
                        self.links_dict[link_id]['parameters'] = parameters
                discFromParent = self.nodes_dict[parentId]
                parentId = discFromParent['parent']

        node['inLinks'] = inLinksList
        node['outLinks'] = outLinksList

        return node

    def create_dot_graph(self):
        dot = Digraph(
            comment='Dependency graph', format='svg', graph_attr={'rankdir': 'LR'}
        )
        drawn_nodes = set()

        for nodeId, node in self.nodes_dict.items():
            if node['hasLinks'] == True and node['level'] == 1:
                dot.node(
                    name=str(nodeId),
                    label='\n'.join([node['label'], node['type']]),
                    tooltip=nodeId,
                )
                drawn_nodes.add(nodeId)

        # filter links on drawn nodes
        filtered_links = {
            linkId: link
            for (linkId, link) in self.links_dict.items()
            if (link['from'] in drawn_nodes and link['to'] in drawn_nodes)
        }
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
            'dotString': self.create_dot_graph().source,
        }
        return self.result

# NOt yet operational
#     def generate_scatter_data_mapping(self):
#         sc_map_parameter_mapping = []
#         scatter_data_ids = set()
#         for sc_disc in self.GEMS_graph.disciplines:
#             if isinstance(sc_disc, SoSScatterData):
#                 scatter_data_ids.add(sc_disc.disc_id)
#                 sc_map = sc_disc.sc_map.map
#                 input_names = sc_disc.sc_map.map['input_name']
#                 output_names = sc_disc.sc_map.map['output_name']
#                 for out_fullname in sc_disc.get_output_data_names():
#                     short_name = out_fullname.split('.')[-1]
#                     index = output_names.index(short_name)
#                     input_fullname = sc_disc.get_var_full_name(
#                         input_names[index], sc_disc._data_in
#                     )
#                     sc_disc_mapping_dict = {
#                         'discipline': sc_disc.disc_id,
#                         'type': type(sc_disc).__name__,
#                         'scatter_var': sc_map['scatter_var_name'],
#                         'input': input_names[index],
#                         'input_full': input_fullname,
#                         'output': short_name,
#                         'output_full': out_fullname,
#                         'scatter_value': out_fullname.split('.')[-2],
#                     }
#                     sc_map_parameter_mapping.append(sc_disc_mapping_dict)
#
#         # remove scatterdata from nodes
#         count = 0
#         for n_id_to_delete in scatter_data_ids:
#             del self.nodes_dict[n_id_to_delete]
#             count += 1
#         print(f'Successfully removed {count} Scatter Data nodes')
#
#         count = 0
#         recurse = True
#         while recurse:
#             # check if some links are from or to scatter data
#             scatter_data_links = [
#                 l
#                 for l in self.links_dict.values()
#                 if l['from'] in scatter_data_ids or l['to'] in scatter_data_ids
#             ]
#             if scatter_data_links is not None and len(scatter_data_links) > 0:
#
#                 # deal with one link at a time
#                 links_to_delete = self.replace_scatter_data_by_links(
#                     sc_map_parameter_mapping,
#                     scatter_data_ids,
#                     l_scatter_dict=scatter_data_links[0],
#                 )
#
#                 # remove links from links dict
#                 for l_id_to_delete in links_to_delete:
#                     del self.links_dict[l_id_to_delete]
#                     count += 1
#
#             else:
#                 recurse = False
#
#         print(f'Successfully removed {count} Scatter Data links')

    def replace_scatter_data_by_links(
        self, sc_map_parameter_mapping, scatter_data_ids, l_scatter_dict
    ):
        links_to_delete = set()
        if l_scatter_dict['from'] in scatter_data_ids:
            # out link of a scatter data
            # recreate all links using parameter exchanged and the mapping of
            # parameters
            for param_out in l_scatter_dict['parameters']:
                # retrieve param_in from scatter_data mapping
                param_mapping = [
                    param_mapping
                    for param_mapping in sc_map_parameter_mapping
                    if param_mapping['discipline'] == l_scatter_dict['from']
                    and param_mapping['output'] in param_out
                ][0]
                param_in = param_mapping['input']

                # look for all in links to the scatter data with this parameter
                in_links = {
                    l_id: l
                    for l_id, l in self.links_dict.items()
                    if l['to'] == param_mapping['discipline']
                    and param_in in l['parameters']
                }

                for l_in_id, l_dict in in_links.items():
                    new_link_id = f'{l_dict["from"]}->{l_scatter_dict["to"]}'
                    scatter_param_name = f'{param_in} -- split[{param_mapping["scatter_value"]}] --> {param_out}'
                    if new_link_id not in self.links_dict:
                        link = {
                            'id': new_link_id,
                            'from': l_dict["from"],
                            'to': l_scatter_dict["to"],
                            'parameters': {scatter_param_name},
                            # 'type': 'scatterDataLink',
                            'type': 'couplingLink',
                        }
                        self.links_dict[new_link_id] = link
                    else:
                        self.links_dict[new_link_id]['parameters'].add(
                            scatter_param_name
                        )

                    # remove parameter from links
                    self.links_dict[l_in_id]['parameters'].remove(param_in)
                    if len(self.links_dict[l_in_id]['parameters']) == 0:
                        links_to_delete.add(l_in_id)
                    print(scatter_param_name)
            # remove parameter from links
            self.links_dict[l_scatter_dict['id']
                            ]['parameters'].remove(param_out)
            if len(self.links_dict[l_scatter_dict['id']]['parameters']) == 0:
                links_to_delete.add(l_scatter_dict['id'])

        elif l_scatter_dict['to'] in scatter_data_ids:
            # in link of a scatter data
            # recreate all links using parameter exchanged and the mapping of
            # parameters
            for param_in in l_scatter_dict['parameters']:
                # retrieve param_out from scatter_data mapping
                param_mapping = [
                    param_mapping
                    for param_mapping in sc_map_parameter_mapping
                    if param_mapping['discipline'] == l_scatter_dict['to']
                    and param_mapping['input'] in param_in
                ][0]
                param_out = param_mapping['output']

                # look for all out links of the scatter data with this
                # parameter
                out_links = {
                    l_id: l
                    for l_id, l in self.links_dict.items()
                    if l['from'] == param_mapping['discipline']
                    and param_in in l['parameters']
                }

                for l_out_id, l_dict in out_links.items():
                    new_link_id = f'{l_scatter_dict["from"]}->{l_dict["to"]}'
                    scatter_param_name = f'{param_in} -- split[{param_mapping["scatter_value"]}] --> {param_out}'
                    if new_link_id not in self.links_dict:
                        link = {
                            'id': new_link_id,
                            'from': l_scatter_dict["from"],
                            'to': l_dict["to"],
                            'parameters': {scatter_param_name},
                            # 'type': 'scatterDataLink',
                            'type': 'couplingLink',
                        }
                        self.links_dict[new_link_id] = link
                    else:
                        self.links_dict[new_link_id]['parameters'].add(
                            scatter_param_name
                        )

                    # remove parameter from links
                    self.links_dict[l_out_id]['parameters'].remove(param_out)
                    if len(self.links_dict[l_out_id]['parameters']) == 0:
                        links_to_delete.add(l_out_id)
                    print(scatter_param_name)
            # remove parameter from links
            self.links_dict[l_scatter_dict['id']
                            ]['parameters'].remove(param_in)
            if len(self.links_dict[l_scatter_dict['id']]['parameters']) == 0:
                links_to_delete.add(l_scatter_dict['id'])

        return links_to_delete
