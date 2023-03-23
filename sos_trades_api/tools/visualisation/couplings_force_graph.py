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

from sostrades_core.api import get_sos_logger
import time


def get_couplings_force_graph(couplingMatrix_df, treeNodes, parameterNodes, hierarchyLinks):

    start_time = time.time()
    logger = get_sos_logger('SoS')

    couplingLinks = []
    groupedLinksDict = {}

    # Create dictionaries to simplify access
    treeNodesDict = {element['id']: element for element in treeNodes}
    parametersDict = {element['id']: element for element in parameterNodes}

    # Create coupling links
    if couplingMatrix_df is not None:
        # convert dataframe to dict
        couplingMatrixDict = couplingMatrix_df.to_dict(orient='index')

        # create a unique set of ids
        idsList = set([key['id'] for key in parameterNodes + treeNodes])

        for row in couplingMatrixDict.values():
            rowLinks = []
            discFromId = row['disc_1']
            discToId = row['disc_2']
            parameterId = row['var_name']

            # Avoid to create links to nodes that do not exists which would
            # crash the drawing of the matrix
            if discFromId in idsList and parameterId in idsList and discToId in idsList:
                rowLinks.append(dict({
                    'id': discFromId + '_TO_' + parameterId + '_TYPE_OUTPUT OF',
                    'source': discFromId,
                    'target': parameterId,
                    'Type': 'OUTPUT_OF',
                    'Size': 3,
                    'ancestors': get_ancestors(treeNodesDict, discFromId),
                    'active': 0
                }))

                rowLinks.append(dict({
                    'id': parameterId + '_TO_' + discToId + '_TYPE_INPUT OF',
                    'source': parameterId,
                    'target': discToId,
                    'Type': 'INPUT_TO',
                    'Size': 3,
                    'ancestors': get_ancestors(treeNodesDict, discToId),
                    'active': 0
                }))

                for link in rowLinks:
                    couplingLinks.append(link)

                # Create an entry for the grouped links
                id = discFromId + '_TO_' + \
                    discToId + '_TYPE_GROUPLINK'

                if id in groupedLinksDict:
                    groupedLinksDict[id]['Size'] += 1
                    groupedLinksDict[id]['parameterList'].append(
                        {'id': parameterId, 'Name': parametersDict.get(parameterId, {}).get('label', '')}),
                    groupedLinksDict[id]['groupedLinks'] += rowLinks,
                    groupedLinksDict[id]['groupedNodes'].append(
                        parameterId)
                else:
                    groupedLinksDict[id] = dict({
                        'id': id,
                        'source': discFromId,
                        'sourceLabel': treeNodesDict[discFromId]['Name'],
                        'target': discToId,
                        'targetLabel': treeNodesDict[discToId]['Name'],
                        'Type': 'parameterExchange',
                        'Size': 1,
                        'parameterList': [{'id': parameterId, 'Name': parametersDict.get(parameterId, {}).get('label', '')}],
                        'sourceAncestors': get_ancestors(treeNodesDict, discFromId),
                        'targetAncestors': get_ancestors(treeNodesDict, discToId),
                        'groupedLinks': rowLinks,
                        'groupedNodes': [parameterId],
                        'active': 1
                    })

            else:
                logger.debug(
                    f'{row["disc_1"]} to {row["disc_2"]} not found in matrix nodes for parameter {row["var_name"]}')

        #  adding the out and in links for each parameter
        for p in parameterNodes:
            inLinks = []
            outLinks = []
            for row in couplingMatrixDict.values():
                discFromId = row['disc_1']
                discToId = row['disc_2']
                parameterId = row['var_name']
                if p['id'] == parameterId:
                    outLinks.append({'link':
                                     discFromId + '_TO_' + parameterId + '_TYPE_OUTPUT OF', 'node': discFromId})
                    inLinks.append({'link':
                                    parameterId + '_TO_' + discToId + '_TYPE_INPUT OF', 'node': discToId})
            p['inLinks'] = inLinks
            p['outLinks'] = outLinks
    else:
        logger.info(f'Coupling Matrix is empty')

    # adding the list of parameters linked to each children for each node
    for node in treeNodes:
        inParameterList = []
        outParameterList = []

        idList = node['childrenIDs'] + [node['id']]

        for p in couplingLinks:
            if p['Type'] == 'OUTPUT_OF':
                if p['source'] in idList:
                    outParameterList.append(p['id'])
            elif p['Type'] == 'INPUT_TO':
                if p['target'] in idList:
                    inParameterList.append(p['id'])

        node['inParameterList'] = inParameterList
        node['outParameterList'] = outParameterList

    couplingMatrixDict = dict({'nodes': treeNodes + parameterNodes,
                               'links': hierarchyLinks + couplingLinks,
                               'treeNodes': treeNodes,
                               'parameterNodes': parameterNodes,
                               'hierarchyLinks': hierarchyLinks,
                               'couplingLinks': couplingLinks,
                               'groupedLinks': hierarchyLinks + list(groupedLinksDict.values())
                               })
    logger.info(
        f'Couplings graph data generated with {len(treeNodes+parameterNodes)} nodes and {len(hierarchyLinks+couplingLinks)} links in {time.time() - start_time} seconds')

    return couplingMatrixDict


def get_ancestors(treeview, startingId):
    ancestors = []
    parentID = treeview[startingId]['Parent Node']
    while parentID != '':
        ancestors.append(parentID)
        parentID = treeview[parentID]['Parent Node']
    return ancestors
