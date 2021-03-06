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
from flask import request, jsonify, make_response
from werkzeug.exceptions import BadRequest


from sos_trades_api.base_server import app
from sos_trades_api.tools.right_management.functional.process_access_right import ProcessAccess
from sos_trades_api.tools.authentication.authentication import auth_required, get_authenticated_user
from sos_trades_api.controllers.sostrades_main.ontology_controller import (
    load_ontology, load_ontology_v1, load_models_status, load_models_links, load_parameters, load_parameter_label_list)


@app.route(f'/api/main/ontology', methods=['POST'])
@auth_required
def load_ontology_request():
    """
    Relay to ontology server to retrieve disciplines and parameters informations

    Request object is intended with the following data structure
        { 
            ontology_request: {
                disciplines: string[], // list of disciplines string identifier
                parameters: string[] // list of parameters string identifier
            }
        }

    Returned response is with the following data structure
        {
            parameters : {
                <parameter_identifier> : {
                    id: string
                    datatype: string
                    definition: string
                    label: string
                    quantityKind: string
                    unit: string
                    uri: string
                    definitionSource: string
                    ACLTag: string
                }
            }
            disciplines {
                <discipline_identifier>: {
                    id: string
                    delivered: string
                    implemented: string
                    label: string
                    modelType: string
                    originSource: string
                    pythonClass: string
                    uri: string
                    validator: string
                    validated: string
                    icon:string
                }
            }
        }

    """

    data_request = request.json.get('ontology_request', None)

    missing_parameter = []
    if data_request is None:
        missing_parameter.append(
            'Missing mandatory parameter: ontology_request')

    if len(missing_parameter) > 0:
        raise BadRequest('\n'.join(missing_parameter))

    resp = make_response(jsonify(load_ontology(data_request)), 200)
    return resp



@app.route(f'/api/main/ontology/v1', methods=['POST'])
@auth_required
def load_ontology_request_v1():
    """
    Relay to ontology server to retrieve disciplines and parameters informations

    Request object is intended with the following data structure
        {
            ontology_request: {
                disciplines: string[], // list of disciplines string identifier
                parameter_usages: string[] // list of parameters string identifier
            }
        }

    Returned response is with the following data structure
        {
            parameter_usages : {
                <parameter_usage_identifier> : {
                    parameter_uri: string
                    parameter_id: string
                    parameter_label: string
                    parameter_definition: string
                    parameter_definitionSource: string
                    parameter_ACLTag: string

                    visibility: string
                    dataframeEditionLocked: string
                    userLevel: string
                    range: string
                    dataframeDescriptor: string
                    structuring: string
                    optional: string
                    namespace: string
                    numerical: string
                    coupling: string
                    io_type: string
                    datatype: string
                    unit: string
                    editable: string
                }
            }
            disciplines {
                <discipline_identifier>: {
                    id: string
                    delivered: string
                    implemented: string
                    label: string
                    modelType: string
                    originSource: string
                    pythonClass: string
                    uri: string
                    validator: string
                    validated: string
                    icon:string
                }
            }
        }

    """

    data_request = request.json.get('ontology_request', None)

    missing_parameter = []
    if data_request is None:
        missing_parameter.append(
            'Missing mandatory parameter: ontology_request')

    if len(missing_parameter) > 0:
        raise BadRequest('\n'.join(missing_parameter))

    resp = make_response(jsonify(load_ontology_v1(data_request)), 200)
    return resp





@app.route(f'/api/main/ontology/models/status', methods=['GET'])
@auth_required
def load_ontology_models_status():
    """
    Relay to ontology server to retrieve the whole sos_trades models status
    Object returned is a form of plotly table data structure

    Returned response is with the following data structure
        {
            headers : string[],
            values: array of {
                details: string,
                header: string,
                value: string
            }
        }
    """
    user = get_authenticated_user()
    process_access = ProcessAccess(user.id)

    resp = make_response(jsonify(load_models_status(process_access.user_process_list)))

    return resp


@app.route(f'/api/main/ontology/models/links', methods=['GET'])
@auth_required
def load_ontology_models_links():
    """
    Relay to ontology server to retrieve the whole sos_trades models links diagram
    Object returned is a form of d3 js data structure

    Returned response is with the following data structure
        { 
            nodes : array of {
                id: string,
                group: integer
            }
            links: array of {
                source: string,
                target: string,
                value: integer
            }

        }
    """
    user = get_authenticated_user()
    process_access = ProcessAccess(user.id)
    return load_models_links(process_access.user_process_list)


@app.route(f'/api/main/ontology/full_parameter_list', methods=['GET'])
@auth_required
def load_ontology_parameters():
    """
    Relay to ontology server to retrieve the whole sos_trades parameters
    Object returned is a form of plotly table data structure

    Returned response is with the following data structure
        {
            headers : string[],
            values: array of {
                details: string,
                header: string,
                value: string
            }
        }
    """
    resp = make_response(jsonify(load_parameters()))

    return resp

@app.route(f'/api/main/ontology/full_parameter_label_list', methods=['GET'])
@auth_required
def load_ontology_parameter_labels():
    """
    Relay to ontology server to retrieve the whole sos_trades parameter labels
    Object returned is a form of plotly table data structure

    Returned response is with the following data structure
        {
            headers : string[],
            values: array of {
                details: string,
                header: string,
                value: string
            }
        }
    """
    resp = make_response(jsonify(load_parameter_label_list()))

    return resp