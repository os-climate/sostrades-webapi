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

"""
tooling to generate D3 js data structure for N2 matrix purpose
"""


def get_couplings_force_graph(coupling_matrix_df, tree_nodes, parameter_nodes, hierarchy_links):

    start_time = time.time()
    logger = logging.getLogger(__name__)

    coupling_links = []
    grouped_links_dict = {}

    # Create dictionaries to simplify access
    tree_nodes_dict = {element["id"]: element for element in tree_nodes}
    parameters_dict = {element["id"]: element for element in parameter_nodes}

    # Create coupling links
    if coupling_matrix_df is not None:
        # convert dataframe to dict
        coupling_matrix_dict = coupling_matrix_df.to_dict(orient="index")

        # create a unique set of ids
        ids_list = set([key["id"] for key in parameter_nodes + tree_nodes])

        for row in coupling_matrix_dict.values():
            row_links = []
            disc_from_id = row["disc_1"]
            disc_to_id = row["disc_2"]
            parameter_id = row["var_name"]

            # Avoid to create links to nodes that do not exists which would
            # crash the drawing of the matrix
            if disc_from_id in ids_list and parameter_id in ids_list and disc_to_id in ids_list:
                row_links.append(dict({
                    "id": disc_from_id + "_TO_" + parameter_id + "_TYPE_OUTPUT OF",
                    "source": disc_from_id,
                    "target": parameter_id,
                    "Type": "OUTPUT_OF",
                    "Size": 3,
                    "ancestors": get_ancestors(tree_nodes_dict, disc_from_id),
                    "active": 0,
                }))

                row_links.append(dict({
                    "id": parameter_id + "_TO_" + disc_to_id + "_TYPE_INPUT OF",
                    "source": parameter_id,
                    "target": disc_to_id,
                    "Type": "INPUT_TO",
                    "Size": 3,
                    "ancestors": get_ancestors(tree_nodes_dict, disc_to_id),
                    "active": 0,
                }))

                for link in row_links:
                    coupling_links.append(link)

                # Create an entry for the grouped links
                id = disc_from_id + "_TO_" + \
                    disc_to_id + "_TYPE_GROUPLINK"

                if id in grouped_links_dict:
                    grouped_links_dict[id]["Size"] += 1
                    grouped_links_dict[id]["parameterList"].append(
                        {"id": parameter_id, "Name": parameters_dict.get(parameter_id, {}).get("label", "")}),
                    grouped_links_dict[id]["groupedLinks"] += row_links,
                    grouped_links_dict[id]["groupedNodes"].append(
                        parameter_id)
                else:
                    grouped_links_dict[id] = dict({
                        "id": id,
                        "source": disc_from_id,
                        "sourceLabel": tree_nodes_dict[disc_from_id]["Name"],
                        "target": disc_to_id,
                        "targetLabel": tree_nodes_dict[disc_to_id]["Name"],
                        "Type": "parameterExchange",
                        "Size": 1,
                        "parameterList": [{"id": parameter_id, "Name": parameters_dict.get(parameter_id, {}).get("label", "")}],
                        "sourceAncestors": get_ancestors(tree_nodes_dict, disc_from_id),
                        "targetAncestors": get_ancestors(tree_nodes_dict, disc_to_id),
                        "groupedLinks": row_links,
                        "groupedNodes": [parameter_id],
                        "active": 1,
                    })

            else:
                logger.debug(
                    f'{row["disc_1"]} to {row["disc_2"]} not found in matrix nodes for parameter {row["var_name"]}')

        #  adding the out and in links for each parameter
        for p in parameter_nodes:
            in_links = []
            out_links = []
            for row in coupling_matrix_dict.values():
                disc_from_id = row["disc_1"]
                disc_to_id = row["disc_2"]
                parameter_id = row["var_name"]
                if p["id"] == parameter_id:
                    out_links.append({"link":
                                     disc_from_id + "_TO_" + parameter_id + "_TYPE_OUTPUT OF", "node": disc_from_id})
                    in_links.append({"link":
                                    parameter_id + "_TO_" + disc_to_id + "_TYPE_INPUT OF", "node": disc_to_id})
            p["in_links"] = in_links
            p["out_links"] = out_links
    else:
        logger.info("Coupling Matrix is empty")

    # adding the list of parameters linked to each children for each node
    for node in tree_nodes:
        in_parameter_list = []
        out_parameter_list = []

        idList = node["childrenIDs"] + [node["id"]]

        for p in coupling_links:
            if p["Type"] == "OUTPUT_OF":
                if p["source"] in idList:
                    out_parameter_list.append(p["id"])
            elif p["Type"] == "INPUT_TO":
                if p["target"] in idList:
                    in_parameter_list.append(p["id"])

        node["in_parameter_list"] = in_parameter_list
        node["out_parameter_list"] = out_parameter_list

    coupling_matrix_dict = dict({"nodes": tree_nodes + parameter_nodes,
                               "links": hierarchy_links + coupling_links,
                               "treeNodes": tree_nodes,
                               "parameterNodes": parameter_nodes,
                               "hierarchyLinks": hierarchy_links,
                               "couplingLinks": coupling_links,
                               "groupedLinks": hierarchy_links + list(grouped_links_dict.values()),
                               })
    logger.info(
        f"Couplings graph data generated with {len(tree_nodes+parameter_nodes)} nodes and {len(hierarchy_links+coupling_links)} links in {time.time() - start_time} seconds")

    return coupling_matrix_dict


def get_ancestors(treeview, starting_id):
    ancestors = []
    parent_id = treeview[starting_id]["Parent Node"]
    while parent_id != "":
        ancestors.append(parent_id)
        parent_id = treeview[parent_id]["Parent Node"]
    return ancestors
