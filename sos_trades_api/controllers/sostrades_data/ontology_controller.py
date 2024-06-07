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

import json
from datetime import datetime, timedelta
from functools import wraps

import requests
from requests.exceptions import ConnectionError

from sos_trades_api.models.custom_json_encoder import CustomJsonEncoder
from sos_trades_api.models.model_status import ModelStatus
from sos_trades_api.server.base_server import app
from sos_trades_api.tools.visualisation.couplings_force_graph import (
    get_couplings_force_graph,
)

"""
Ontology Functions
"""


def ontology_enable(default_returned_valued):
    """
    :param default_returned_valued: value to return instead of launching decorated function
    :type  default_returned_valued: any

    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):

            ontology_endpoint = app.config["SOS_TRADES_ONTOLOGY_ENDPOINT"]

            if len(ontology_endpoint) == 0:
                app.logger.info(
                    'Ontology endpoint not defined, no request executed')
                return default_returned_valued

            grace_period = app.config.get("ONTOLOGY_GRACE_PERIOD")
            if grace_period is not None:
                if datetime.now() > grace_period:
                    app.config["ONTOLOGY_GRACE_PERIOD"] = None
                else:
                    app.logger.info(
                        f'Ontology grace period not finished {grace_period}, no request executed'
                    )
                    return default_returned_valued

            return func(*args, **kwargs)

        return wrapper

    return decorator


def set_ontology_grace_period():
    """
    Set a one minute grace period that disable all ontology request
    it allows to avoid multiple failed request and associated loss of performance

    """
    grace_period = datetime.now() + timedelta(minutes=10)
    app.config["ONTOLOGY_GRACE_PERIOD"] = grace_period
    app.logger.exception(
        f'An exception occurs when trying to reach Ontology server, grace period has been set to {grace_period}'
    )


@ontology_enable({})
def load_ontology(ontology_request: dict)->dict:
    """Given a dictionary of entities, return ontology metadata

    :params: request
    :type: dict

    Possible keys are:
    {
        'disciplines':  [disciplinesId],
        'parameters':   [parametersId],
        'process':      [processId],
        'repository':   [repositoryId]
    }

    :return: metadata dict
        {
        'disciplines':  {disciplinesId:metadata},
        'parameters':   {parametersId:metadata},
        'process':      {processId:metadata},
        'repository':   {repositoryId:metadata}
    }
    """
    ssl_path = app.config['INTERNAL_SSL_CERTIFICATE']
    ontology_endpoint = app.config["SOS_TRADES_ONTOLOGY_ENDPOINT"]
    ontology_response_data = {}

    complete_url = f'{ontology_endpoint}'

    data = {'ontology_request': ontology_request}

    try:
        resp = requests.request(
            method='POST', url=complete_url, json=data, verify=ssl_path
        )

        if resp.status_code == 200:
            ontology_response_data = resp.json()

    except ConnectionError:
        set_ontology_grace_period()
    except:
        app.logger.exception(
            'An exception occurs when trying to reach Ontology server')

    return ontology_response_data


@ontology_enable({})
def load_ontology_usages(ontology_request):
    """Given a dictionary of entities, return ontology metadata

    :params: request
    :type: dict

    Possible keys are:
    {
        'disciplines':  [disciplinesId],
        'parameter_usages':   [parametersId],
    }

    :return: metadata dict
        {
        'disciplines':  {disciplinesId:metadata},
        'parameter_usages':   {parametersId:metadata},
    }
    """
    ssl_path = app.config['INTERNAL_SSL_CERTIFICATE']
    ontology_endpoint = app.config["SOS_TRADES_ONTOLOGY_ENDPOINT"]
    ontology_response_data = {}

    complete_url = f'{ontology_endpoint}/v1/study'

    data = {'study_ontology_request': ontology_request}

    try:
        resp = requests.request(
            method='POST', url=complete_url, json=data, verify=ssl_path
        )

        if resp.status_code == 200:
            ontology_response_data = resp.json()

    except ConnectionError:
        set_ontology_grace_period()
    except:
        app.logger.exception(
            'An exception occurs when trying to reach Ontology server')

    return ontology_response_data


@ontology_enable({})
def load_models():
    """
    Load all models from ontology
    :return: model status object
    """
    ssl_path = app.config['INTERNAL_SSL_CERTIFICATE']
    ontology_endpoint = app.config["SOS_TRADES_ONTOLOGY_ENDPOINT"]
    ontology_response_data = {}

    complete_url = f'{ontology_endpoint}/v1/full_discipline_list'

    try:
        resp = requests.request(
            method='GET', url=complete_url, verify=ssl_path
        )

        if resp.status_code == 200:
            ontology_response_data = resp.json()

    except ConnectionError:
        set_ontology_grace_period()
    except:
        app.logger.exception(
            'An exception occurs when trying to reach Ontology server')

    return ontology_response_data


@ontology_enable({})
def load_models_status_filtered(process_list):
    """Given a process list identifier, return process status

    :params: process_list, list of process identifier
    :type: list

    :return: model status object
    """
    ssl_path = app.config['INTERNAL_SSL_CERTIFICATE']
    ontology_endpoint = app.config["SOS_TRADES_ONTOLOGY_ENDPOINT"]
    ontology_response_data = {}

    complete_url = f'{ontology_endpoint}/models/status-filtered'

    linked_process_dict = {}
    for pr in process_list:
        if pr.process_path in linked_process_dict:
            linked_process_dict[pr.process_path].append(pr.name)
        else:
            linked_process_dict[pr.process_path] = [pr.name]

    data = {'linked_process_dict': linked_process_dict}

    try:
        resp = requests.request(
            method='POST', url=complete_url, json=data, verify=ssl_path
        )

        if resp.status_code == 200:
            ontology_response_data = resp.json()

    except ConnectionError:
        set_ontology_grace_period()
    except:
        app.logger.exception(
            'An exception occurs when trying to reach Ontology server')

    # Deserialized Model status list
    model_list = []
    for md in ontology_response_data:
        new_model = ModelStatus()
        new_model.deserialize(json_dict=md)
        model_list.append(new_model)
    models_status_sorted = sorted(
        model_list, key=lambda x: x.name.lower().strip())

    return models_status_sorted


@ontology_enable({})
def load_parameters():
    """return parameter glossary

    :return: parameters list
    """
    ssl_path = app.config['INTERNAL_SSL_CERTIFICATE']
    ontology_endpoint = app.config["SOS_TRADES_ONTOLOGY_ENDPOINT"]
    ontology_response_data = {}

    complete_url = f'{ontology_endpoint}/v1/full_parameter_list'

    try:
        resp = requests.request(
            method='GET', url=complete_url, verify=ssl_path
        )

        if resp.status_code == 200:
            ontology_response_data = resp.json()

    except ConnectionError:
        set_ontology_grace_period()
    except:
        app.logger.exception(
            'An exception occurs when trying to reach Ontology server')

    return ontology_response_data


@ontology_enable({})
def load_parameter_label_list():
    """return parameter glossary

    :return: parameters list
    """
    ssl_path = app.config['INTERNAL_SSL_CERTIFICATE']
    ontology_endpoint = app.config["SOS_TRADES_ONTOLOGY_ENDPOINT"]
    ontology_response_data = {}

    complete_url = f'{ontology_endpoint}/v1/full_parameter_label_list'

    try:
        resp = requests.request(
            method='POST', url=complete_url, verify=ssl_path
        )

        if resp.status_code == 200:
            ontology_response_data = resp.json()

    except ConnectionError:
        set_ontology_grace_period()
    except:
        app.logger.exception(
            'An exception occurs when trying to reach Ontology server')

    return ontology_response_data


@ontology_enable({})
def load_markdown_documentation_metadata(identifier):
    """Given a process identifier or a model identifier, return a markdown documentation

       :params: identifier, identifier of process or model
       :type: string

       :return: a array of markdown documentation
       """
    ssl_path = app.config['INTERNAL_SSL_CERTIFICATE']
    ontology_endpoint = app.config["SOS_TRADES_ONTOLOGY_ENDPOINT"]
    ontology_response_data = {}
    complete_url = f'{ontology_endpoint}/markdown_documentation/{identifier}'

    try:
        resp = requests.request(
            method='GET', url=complete_url, verify=ssl_path
        )

        if resp.status_code == 200:
            ontology_response_data = resp.json()

    except ConnectionError:
        set_ontology_grace_period()
    except:
        app.logger.exception(
            'An exception occurs when trying to reach Ontology server')

    return ontology_response_data


@ontology_enable({})
def load_ontology_processes():
    """return process list

    :params: process_list, list of process identifier
    :type: list

    :return: model status object
    """
    ssl_path = app.config['INTERNAL_SSL_CERTIFICATE']
    ontology_endpoint = app.config["SOS_TRADES_ONTOLOGY_ENDPOINT"]
    ontology_response_data = {}

    complete_url = f'{ontology_endpoint}/v1/full_process_list'

    try:
        resp = requests.request(
            method='GET', url=complete_url, verify=ssl_path
        )

        if resp.status_code == 200:
            ontology_response_data = resp.json()

    except ConnectionError:
        set_ontology_grace_period()
    except:
        app.logger.exception(
            'An exception occurs when trying to reach Ontology server')

    process_list_sorted = sorted(
        ontology_response_data, key=lambda x: x['label'].lower()
    )

    return process_list_sorted


@ontology_enable({})
def load_process_metadata(process_identifier):
    """Given a process identifier, return ontology metadata

    :params: process_identifier
    :type: string

    :return: process metadata
    """
    ssl_path = app.config['INTERNAL_SSL_CERTIFICATE']
    ontology_endpoint = app.config["SOS_TRADES_ONTOLOGY_ENDPOINT"]
    ontology_response_data = {}

    complete_url = f'{ontology_endpoint}/process/{process_identifier}'

    try:
        resp = requests.request(
            method='GET', url=complete_url, verify=ssl_path)

        if resp.status_code == 200:
            ontology_response_data = resp.json()

    except ConnectionError:
        set_ontology_grace_period()
    except:
        app.logger.exception(
            'An exception occurs when trying to reach Ontology server')

    return ontology_response_data


@ontology_enable({})
def load_processes_metadata(processes_identifier):
    """Given a list of process identifier, return ontology metadata

    :params: processes_identifier
    :type: list

    :return: processes metadata
    """
    ssl_path = app.config['INTERNAL_SSL_CERTIFICATE']
    ontology_endpoint = app.config["SOS_TRADES_ONTOLOGY_ENDPOINT"]
    ontology_response_data = {}

    complete_url = f'{ontology_endpoint}/process/by/names'

    data = {'processes_name': processes_identifier}

    try:
        resp = requests.request(
            method='POST', url=complete_url, json=data, verify=ssl_path
        )

        if resp.status_code == 200:
            ontology_response_data = resp.json()

    except ConnectionError:
        set_ontology_grace_period()
    except:
        app.logger.exception(
            'An exception occurs when trying to reach Ontology server')

    return ontology_response_data


@ontology_enable({})
def load_repository_metadata(repository_identifier):
    """Given a repository identifier, return ontology metadata

    :params: repository_identifier
    :type: string

    :return: repository metadata
    """
    ssl_path = app.config['INTERNAL_SSL_CERTIFICATE']
    ontology_endpoint = app.config["SOS_TRADES_ONTOLOGY_ENDPOINT"]
    ontology_response_data = {}

    complete_url = f'{ontology_endpoint}/repository/{repository_identifier}'

    try:
        resp = requests.request(
            method='GET', url=complete_url, verify=ssl_path)

        if resp.status_code == 200:
            ontology_response_data = resp.json()

    except ConnectionError:
        set_ontology_grace_period()
    except:
        app.logger.exception(
            'An exception occurs when trying to reach Ontology server')

    return ontology_response_data


@ontology_enable({})
def load_repositories_metadata(repositories_identifier):
    """Given a list of repository identifier, return ontology metadata

    :params: repositories_identifier
    :type: list

    :return: repositories metadata
    """
    ssl_path = app.config['INTERNAL_SSL_CERTIFICATE']
    ontology_endpoint = app.config["SOS_TRADES_ONTOLOGY_ENDPOINT"]
    ontology_response_data = {}

    complete_url = f'{ontology_endpoint}/repository/by/names'

    data = {'repositories_name': repositories_identifier}

    try:
        resp = requests.request(
            method='POST', url=complete_url, json=data, verify=ssl_path
        )

        if resp.status_code == 200:
            ontology_response_data = resp.json()

    except ConnectionError:
        set_ontology_grace_period()
    except:
        app.logger.exception(
            'An exception occurs when trying to reach Ontology server')

    return ontology_response_data


@ontology_enable({})
def load_ontology_general_information():
    """ Methods returning generic information concerning the current ontology

        Returned response is with the following data structure
            {
                description:string,
                version:string,
                iri: string,
                last_updated:string
                entity_count:{
                    'Code Repositories':integer,
                    'Process Repositories':integer,
                    'Processes':integer,
                    'Models':integer,
                    'Parameters':integer,
                    'Usecases':integer,
                }
            }
    """
    ssl_path = app.config['INTERNAL_SSL_CERTIFICATE']
    ontology_endpoint = app.config["SOS_TRADES_ONTOLOGY_ENDPOINT"]
    ontology_response_data = {}

    complete_url = f'{ontology_endpoint}/v1/general_information'

    try:
        resp = requests.request(
            method='GET', url=complete_url, verify=ssl_path
        )
        if resp.status_code == 200:
            ontology_response_data = resp.json()

    except ConnectionError:
        set_ontology_grace_period()
    except:
        app.logger.exception(
            'An exception occurs when trying to reach Ontology server')

    return ontology_response_data


@ontology_enable({})
def load_n2_matrix(treeview):
    """Regarding the given treeview object, generate the n2 matrix parameters associated to the process

    :params: treeview
    :type: sostrades_core.tools.tree.treeview.Treeview

    :return: tuple of parameters
    """
    ssl_path = app.config['INTERNAL_SSL_CERTIFICATE']
    ontology_endpoint = app.config["SOS_TRADES_ONTOLOGY_ENDPOINT"]
    ontology_response_data = {}

    complete_url = f'{ontology_endpoint}/n2'

    data = {'treeview': treeview.to_dict()}

    try:
        resp = requests.request(
            method='POST',
            url=complete_url,
            data=json.dumps(data, cls=CustomJsonEncoder),
            headers={'Content-Type': 'application/json'},
            verify=ssl_path,
        )

        if resp.status_code == 200:
            ontology_response_data = resp.json()

    except ConnectionError:
        set_ontology_grace_period()
    except:
        app.logger.exception(
            'An exception occurs when trying to reach Ontology server')

    return (
        ontology_response_data['tree_nodes'],
        ontology_response_data['parameter_nodes'],
        ontology_response_data['hierarchy_links'],
    )


def generate_n2_matrix(study_case_manager):
    """regarding the study case given as parameter , generate the N2 diagram

    :params: study_case_manager
    :type: sos_trades_api.tools.loading.study_case_manager.StudyCaseManager

    :return: N2 diagram object
    """

    n2_diagram = {}
    try:
        couplings = study_case_manager.execution_engine.root_process.export_couplings()

    except:
        pass
    try:
        treeNodes, parameterNodes, hierarchyLinks = load_n2_matrix(
            study_case_manager.execution_engine.get_treeview()
        )

        n2_diagram = get_couplings_force_graph(
            couplings, treeNodes, parameterNodes, hierarchyLinks
        )

    except:
        n2_diagram = {}

    return n2_diagram
