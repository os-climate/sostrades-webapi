'''
Copyright 2022 Airbus SAS
Modifications on 2024/05/16-2024/06/13 Copyright 2024 Capgemini

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
from graphviz import Digraph
from sostrades_core.study_manager.base_study_manager import BaseStudyManager
from sostrades_core.study_manager.study_manager import StudyManager

from sos_trades_api.controllers.sostrades_data.ontology_controller import load_ontology


class InterfaceDiagramGenerator:
    def __init__(self, study: StudyManager, draw_subgraphs=True):
        self.study = study
        self.coupling_graph = (
            self.study.execution_engine.root_process.coupling_structure.graph
        )
        self.couplings_list = self.coupling_graph.get_disciplines_couplings()
        self.treeview = self.study.execution_engine.get_treeview()
        self.disciplines_dict = (
            self.study.ee.dm.convert_disciplines_dict_with_full_name()
        )
        self.interface_diagram_data = {
            "discipline_nodes": [],
            "parameter_nodes": [],
            "links": [],
            "dotString": "",
        }
        self.color_match_set = list()
        self.color_scheme_max = 12
        self.draw_subgraphs = draw_subgraphs
        if self.draw_subgraphs:
            base_study = BaseStudyManager(
                self.study.repository_name, self.study.process_name, "base_study",
            )
            base_disciplines_dict = (
                base_study.ee.dm.convert_disciplines_dict_with_full_name()
            )
            self.base_namespace_dict = self.generate_base_namespace_dict(
                base_disciplines_dict,
            )
            self.base_namespace_tree = self.get_children_ns_from_dict(
                ns="",
                base_namespace_dict=self.base_namespace_dict,
                ns_already_used=set(),
            )

    def generate_interface_diagram_data(self):
        try:
            discipline_node_list = self.generate_disciplines_data()
            parameter_nodes_list, links_list = self.generate_parameters_and_links_data(
                discipline_node_list=discipline_node_list,
            )
            parameter_nodes_list = self.add_ontology_metadata_to_parameter(
                parameter_nodes_list,
            )
            discipline_node_list = self.filter_discipline_with_no_exchanges(
                discipline_node_list=discipline_node_list, links_list=links_list,
            )
            digraph = self.create_dot_graph(
                discipline_node_list=discipline_node_list,
                parameter_nodes_list=parameter_nodes_list,
                links_list=links_list,
            )
            self.interface_diagram_data = {
                "discipline_nodes": discipline_node_list,
                "parameter_nodes": parameter_nodes_list,
                "links": links_list,
                "dotString": digraph.source,
            }
            return self.interface_diagram_data
        except Exception as ex:
            raise ex

    def generate_disciplines_data(self) -> list:
        discipline_node_list = []
        base_namespace_list = list(self.base_namespace_dict.keys())
        unique_disc_ids = set()
        for ns_node, disc_list in self.disciplines_dict.items():
            for disc_dict in disc_list:
                disc = disc_dict["reference"]
                label = ""
                if hasattr(disc, "_ontology_data"):
                    label = disc._ontology_data.get("label", "")
                # check if discipline has coupling structure and retrieve it
                # this is particularly usefull for subprocess like DOE /
                # GridSearch
                if hasattr(disc, "coupling_structure"):
                    discipline_coupling_list = (
                        disc.coupling_structure.graph.get_disciplines_couplings()
                    )
                    # complement coupling list with discipline couplings
                    self.couplings_list = self.couplings_list + discipline_coupling_list
                classname = disc_dict.get("classname", None)
                if classname == "ProxyDiscipline":
                    classname = type(disc.discipline_wrapp.wrapper).__name__
                if classname not in ["SoSCoupling", "ProxyCoupling"]:
                    disc_id = ".".join(ns_node.split(".")[1:]) + "." + classname
                    if disc_id not in unique_disc_ids:
                        unique_disc_ids.add(disc_id)
                        namespace = ".".join(ns_node.split(".")[1:])
                        base_namespace = self.get_base_namespace(
                            namespace=namespace, base_namespace_list=base_namespace_list,
                        )
                        disc_node_info = {
                            "id": disc_id,
                            "type": "DisciplineNode",
                            "namespace": ".".join(ns_node.split(".")[1:]),
                            "cluster": base_namespace,
                            "classname": classname,
                            # 'model_name':disc_dict.get('model_name',None),
                            "model_name_full_path": disc_dict.get(
                                "model_name_full_path", None,
                            ),
                            "ontology_label": label,
                        }
                        discipline_node_list.append(disc_node_info)
        return discipline_node_list

    def generate_parameters_and_links_data(self, discipline_node_list: list) -> tuple:
        links_list = []
        parameters_list = []
        unique_links_ids = set()
        unique_parameters_ids = set()
        parameters_node_info = None
        try:
            for (disc_from, disc_to, edge_parameters_list) in self.couplings_list:
                disc_from_classname = type(disc_from).__name__
                if disc_from_classname == "ProxyDiscipline":
                    disc_from_classname = type(
                        disc_from.discipline_wrapp.wrapper,
                    ).__name__
                disc_from_id = (
                    ".".join(disc_from.get_disc_full_name().split(".")[1:])
                    + "."
                    + disc_from_classname
                )
                disc_to_classname = type(disc_to).__name__
                if disc_to_classname == "ProxyDiscipline":
                    disc_to_classname = type(disc_to.discipline_wrapp.wrapper).__name__
                disc_to_id = (
                    ".".join(disc_to.get_disc_full_name().split(".")[1:])
                    + "."
                    + disc_to_classname
                )
                disc_from_namespace_list = [
                    d["namespace"] for d in discipline_node_list if d["id"] == disc_from_id
                ]
                disc_from_namespace = (
                    disc_from_namespace_list[0]
                    if disc_from_namespace_list
                    else disc_from_id
                )

                disc_to_namespace_list = [
                    d["namespace"] for d in discipline_node_list if d["id"] == disc_to_id
                ]
                disc_to_namespace = (
                    disc_to_namespace_list[0] if disc_to_namespace_list else disc_to_id
                )

                for output_param in edge_parameters_list:
                    param_id = ".".join(output_param.split(".")[1:])
                    output_param_data = disc_from.ee.dm.get_data(output_param)
                    parameter_name = output_param_data.get("var_name", "")
                    parameter_type = output_param_data.get("type", "")
                    descriptor = None
                    value = output_param_data.get("value", None)
                    if value is not None:
                        if parameter_type == "dataframe":
                            descriptor = list(value.columns)
                        elif parameter_type == "dict":
                            descriptor = list(value.keys())

                    # by default, we retrieve the namespace of the discipline outputting this parameter
                    parameter_namespace = disc_from_namespace

                    # check if disc_from is a coupling
                    if type(disc_from).__name__ == "SoSCoupling":
                        # in that case, we will try to found the real discipline from which the parameter is outputting
                        disc_origin_uuid = self.study.ee.dm.get_data(output_param)[
                            "model_origin"
                        ]
                        disc_origin = self.study.ee.dm.get_discipline(disc_origin_uuid)
                        disc_from_id = (
                            ".".join(disc_origin.get_disc_full_name().split(".")[1:])
                            + "."
                            + type(disc_origin).__name__
                        )
                        disc_origin_namespace_list = [
                            d["namespace"]
                            for d in discipline_node_list
                            if d["id"] == disc_from_id
                        ]
                        parameter_namespace = (
                            disc_origin_namespace_list[0]
                            if disc_origin_namespace_list
                            else disc_from_id
                        )
                    if type(disc_to).__name__ == "SoSCoupling":
                        # case that is not yet taken into account
                        print("parameter going to a SoSCouling, not taken care of")

                    # add parameter node if does not exists
                    if param_id not in unique_parameters_ids:
                        unique_parameters_ids.add(param_id)
                        parameters_node_info = {
                            "id": param_id,
                            "namespace": parameter_namespace,
                            "type": "ParameterNode",
                            "parameter_name": parameter_name,
                            "datatype": parameter_type,
                            "unit": output_param_data.get("unit", ""),
                            "descriptor": descriptor,
                        }
                    parameters_list.append(parameters_node_info)

                    # add link from out disc to parameter and from parameter to in
                    # disc
                    out_link_id = f"{disc_from_id}->{param_id}"
                    in_link_id = f"{param_id}->{disc_to_id}"
                    weight = 0
                    if out_link_id not in unique_links_ids:
                        unique_links_ids.add(out_link_id)
                        out_link_info = {
                            "id": out_link_id,
                            "from": disc_from_id,
                            "to": param_id,
                            "constraint": "false",
                            "weight": weight,
                        }
                        links_list.append(out_link_info)
                    if in_link_id not in unique_links_ids:
                        unique_links_ids.add(in_link_id)
                        constraint = "true"
                        if disc_from_namespace == disc_to_namespace:
                            constraint = "false"
                            weight = 3
                        in_link_info = {
                            "id": in_link_id,
                            "from": param_id,
                            "to": disc_to_id,
                            "constraint": constraint,
                            "weight": weight,
                        }
                        links_list.append(in_link_info)
            return parameters_list, links_list
        except Exception as ex:
            raise ex

    def create_dot_graph(
        self, discipline_node_list: list, parameter_nodes_list: list, links_list: list,
    ) -> Digraph:
        dot = Digraph(
            comment="Dependency graph",
            format="svg",
            engine="dot",
            graph_attr={
                "rankdir": "LR",
                "overlap": "false",
                "label": self.study.process_name,
                "fontsize": "20",
                # 'mindist':'0.2',
                # 'ranksep':'2',
            },
            node_attr={"colorscheme": "set312", "nodesep": "0.04"},
            # edge_attr={'minlen':'0'},
        )
        if self.draw_subgraphs:
            main_nodes = [n for n in discipline_node_list if n["namespace"] == ""]
            # draw discipline nodes
            for node_dict in main_nodes:
                self.draw_discipline_node(digraph=dot, node_info_dict=node_dict)
            main_parameters_nodes = [
                n for n in parameter_nodes_list if n["namespace"] == ""
            ]
            # draw parameter nodes
            for node_dict in main_parameters_nodes:
                self.draw_parameter_node(digraph=dot, node_info_dict=node_dict)
            self.generate_subgraph(
                subgraph_list=self.base_namespace_tree[""],
                parent_graph=dot,
                discipline_node_list=discipline_node_list,
                parameter_nodes_list=parameter_nodes_list,
            )

        else:
            # draw discipline nodes
            for node_dict in discipline_node_list:
                self.draw_discipline_node(digraph=dot, node_info_dict=node_dict)

            # draw parameter nodes
            for node_dict in parameter_nodes_list:
                self.draw_parameter_node(digraph=dot, node_info_dict=node_dict)

        for link_dict in links_list:
            dot.edge(
                tail_name=link_dict["from"],
                head_name=str(link_dict["to"]),
                label="",
                _attributes={
                    "style": "dashed",
                    # 'constraint':link_dict['constraint']
                    # 'weight':str(link_dict['weight']),
                },
            )

        return dot

    def draw_discipline_node(self, digraph: Digraph, node_info_dict: dict) -> None:
        node_namespace_simple = node_info_dict["namespace"].replace(
            digraph.graph_attr.get("label", ""), "",
        )
        ontology_label = node_info_dict["ontology_label"]
        if ontology_label == "":
            ontology_label = node_info_dict["classname"]
        if node_namespace_simple != "":
            if node_namespace_simple[0] == ".":
                node_namespace_simple = node_namespace_simple[1:]
            label = f"{ontology_label}\n{node_namespace_simple}"
        else:
            label = f"{ontology_label}"
        digraph.node(
            name=str(node_info_dict["id"]),
            label=label,
            tooltip=f'{node_info_dict["model_name_full_path"]}',
            _attributes={
                "shape": "ellipse",
                "style": "filled",
                "fillcolor": str(self.get_color(node_info_dict["namespace"])),
                "margin": "0.01",
                "ordering": "out",
            },
        )

    def draw_parameter_node(self, digraph: Digraph, node_info_dict: dict) -> None:
        descriptor = ""
        if node_info_dict["descriptor"] is not None:
            if node_info_dict["datatype"] == "dataframe":
                descriptor = (
                    "|{Columns:|{" + "|".join(node_info_dict["descriptor"]) + "}}"
                )
            elif node_info_dict["datatype"] == "dict":
                descriptor = "|{Keys:|{" + "|".join(node_info_dict["descriptor"]) + "}}"
        parameter_label = node_info_dict["parameter_name"]
        if node_info_dict.get("label", "") != "":
            if len(parameter_label.split(".")) > 1:
                parameter_label = (
                    node_info_dict.get("label", "")
                    + " - "
                    + ".".join(parameter_label.split(".")[:-1])
                )
            else:
                parameter_label = node_info_dict.get("label", "")
        digraph.node(
            name=str(node_info_dict["id"]),
            # horizontal
            # label="{"+f'{node_info_dict["parameter_name"]}|Unit:{node_info_dict["unit"]}|Datatype:{node_info_dict["datatype"]}'+"}| |" + descriptor,
            # vertical
            # label=f'{parameter_label}|Unit:{node_info_dict["unit"]}, Datatype:{node_info_dict["datatype"]}|'+"{Columns:|"+descriptor+"}",
            label=f'{parameter_label}|Unit:{node_info_dict["unit"]}, Datatype:{node_info_dict["datatype"]}'
            + descriptor,
            tooltip=f'{node_info_dict["parameter_name"]}',
            _attributes={
                "shape": "record",
                "fontsize": "10",
                "margin": "0.01",
            },
        )

    def get_color(self, nodeType: str) -> int:
        # add nodeType to color match set
        if nodeType not in self.color_match_set:
            self.color_match_set.append(nodeType)
        color_index = self.color_match_set.index(nodeType)
        return color_index % self.color_scheme_max + 1

    def get_namespace_list(self, discipline_dict: dict) -> list:
        namespace_ids = set()
        for ns_node in discipline_dict:
            namespace = ".".join(ns_node.split(".")[1:])
            namespace_ids.add(namespace)
        return sorted(list(namespace_ids))

    def get_base_namespace(self, namespace: str, base_namespace_list: list) -> str:
        node_base_namespace = ""
        for base_ns in base_namespace_list:
            if base_ns == namespace:
                return base_ns
            if base_ns in namespace and len(base_ns) > len(node_base_namespace):
                node_base_namespace = base_ns
        return node_base_namespace

    def generate_base_namespace_dict(self, base_discipline_dict: dict) -> dict:
        # namespace list
        base_namespace_list = self.get_namespace_list(base_discipline_dict)

        # add SoSCouplings namespace because when it is a multiscenario, it is useful to create a base namespace for each scenario
        for ns_node, disc_list in self.disciplines_dict.items():
            for disc_dict in disc_list:
                if disc_dict.get("classname", None) == "SoSCoupling":
                    new_base_namespace = ".".join(ns_node.split(".")[1:])
                    if (
                        new_base_namespace != ""
                        and new_base_namespace not in base_namespace_list
                    ):
                        base_namespace_list.append(new_base_namespace)

        # add possible missing parent namespaces
        parent_ns_to_add = set()
        for ns in base_namespace_list:
            ns_split = ns.split(".")
            for i in range(len(ns_split)):
                sub_ns = ".".join(ns_split[:-i])
                if sub_ns not in base_namespace_list:
                    parent_ns_to_add.add(sub_ns)
        base_namespace_list = sorted(base_namespace_list + list(parent_ns_to_add))

        full_namespace_list = self.get_namespace_list(self.disciplines_dict)
        base_namespace_dict = {base_ns: [] for base_ns in base_namespace_list}

        # fill base namespace with node namespace
        for namespace in full_namespace_list:
            node_base_namespace = self.get_base_namespace(
                namespace, base_namespace_list,
            )
            # add namespace to base ns dict
            base_namespace_dict[node_base_namespace].append(namespace)

        return base_namespace_dict

    def get_children_ns_from_dict(self, ns, base_namespace_dict, ns_already_used):
        ns_tree = {"disciplines": base_namespace_dict.get(ns, []), "sub_groups": []}
        ns_already_used.add(ns)
        for sub_ns in base_namespace_dict.keys():
            if (ns == "" and len(sub_ns.split(".")) == 1 and sub_ns != "") or (
                len(ns.split(".")) + 1 == len(sub_ns.split(".")) and ns in sub_ns
            ):
                if sub_ns not in ns_already_used:
                    sub_namespace_tree = self.get_children_ns_from_dict(
                        sub_ns, base_namespace_dict, ns_already_used,
                    )
                    if (
                        len(list(sub_namespace_tree.values())[0]["disciplines"]) > 0
                        or len(list(sub_namespace_tree.values())[0]["sub_groups"]) > 0
                    ):
                        ns_tree["sub_groups"].append(sub_namespace_tree)

        namespace_tree = {ns: ns_tree}
        return namespace_tree

    def generate_subgraph(
        self,
        subgraph_list: dict,
        parent_graph: Digraph,
        discipline_node_list: list,
        parameter_nodes_list: list,
    ) -> Digraph:
        for subgraph_dict in subgraph_list.get("sub_groups", []):
            for subgraph_name, subgraph_children_list in subgraph_dict.items():
                subgraph = Digraph(
                    name="cluster_" + subgraph_name,
                    comment=subgraph_name,
                    graph_attr={
                        "label": subgraph_name,
                        # 'color':str(self.get_color(subgraph_name)),
                        "style": "dotted",
                        "rank": "source",
                    },
                )
                subgraph_nodes_namespace_list = subgraph_children_list.get(
                    "disciplines", [],
                )
                subgraph_nodes = [
                    n
                    for n in discipline_node_list
                    if n["namespace"] in subgraph_nodes_namespace_list
                ]

                # draw discipline nodes
                for node_dict in subgraph_nodes:
                    self.draw_discipline_node(
                        digraph=subgraph, node_info_dict=node_dict,
                    )
                subgraph_parameters_nodes = [
                    n
                    for n in parameter_nodes_list
                    if n["namespace"] in subgraph_nodes_namespace_list
                ]
                # draw parameter nodes
                for node_dict in subgraph_parameters_nodes:
                    self.draw_parameter_node(digraph=subgraph, node_info_dict=node_dict)
                if len(subgraph_children_list) > 0:
                    self.generate_subgraph(
                        subgraph_list=subgraph_children_list,
                        parent_graph=subgraph,
                        discipline_node_list=discipline_node_list,
                        parameter_nodes_list=parameter_nodes_list,
                    )
                if len(subgraph_children_list) > 0 or len(subgraph_nodes) > 0:
                    parent_graph.subgraph(
                        graph=subgraph,
                    )
        return parent_graph

    def add_ontology_metadata_to_parameter(self, parameter_nodes_list: list) -> list:
        parameter_list = [
            p["parameter_name"].split(".")[-1] for p in parameter_nodes_list
        ]
        ontology_request = {
            "parameters": parameter_list,
        }
        ontology_response_data = load_ontology(ontology_request=ontology_request)

        complemented_parameter_nodes_list = parameter_nodes_list
        if ontology_response_data is not None:
            ontology_parameters_data = ontology_response_data.get("parameters", None)
            if ontology_parameters_data is not None:
                complemented_parameter_nodes_list = []
                for parameter_dict in parameter_nodes_list:
                    parameter_dict["label"] = ontology_parameters_data.get(
                        parameter_dict["parameter_name"].split(".")[-1], {"label": ""},
                    )["label"]
                    complemented_parameter_nodes_list.append(parameter_dict)
        return complemented_parameter_nodes_list

    def filter_discipline_with_no_exchanges(
        self, discipline_node_list: list, links_list: list,
    ) -> list:
        filtered_discipline_node_list = []
        for disc_dict in discipline_node_list:
            disc_links = [
                link["id"]
                for link in links_list
                if link["from"] == disc_dict["id"] or link["to"] == disc_dict["id"]
            ]
            if len(disc_links) > 0:
                disc_dict["couplings_number"] = len(disc_links)
                filtered_discipline_node_list.append(disc_dict)
        return filtered_discipline_node_list
