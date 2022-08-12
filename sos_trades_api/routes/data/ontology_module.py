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
from flask import request, jsonify, make_response, session
from werkzeug.exceptions import BadRequest

from sos_trades_api.server.base_server import app
from sos_trades_api.tools.right_management.functional.process_access_right import ProcessAccess
from sos_trades_api.tools.authentication.authentication import auth_required, get_authenticated_user
from sos_trades_api.controllers.sostrades_data.ontology_controller import (
    load_models_status, load_parameters, load_parameter_label_list,
    load_markdown_documentation_metadata, load_ontology_processes, load_ontology_usages,
    load_ontology_general_information)


@app.route(f'/api/data/ontology/ontology-usages', methods=['POST'])
@auth_required
def load_ontology_request_usages():
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

    resp = make_response(jsonify(load_ontology_usages(data_request)), 200)
    return resp


@app.route(f'/api/data/ontology/models/status', methods=['GET'])
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


@app.route(f'/api/data/ontology/full_parameter_list', methods=['GET'])
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


@app.route(f'/api/data/ontology/full_parameter_label_list', methods=['GET'])
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


@app.route(f'/api/data/ontology/<string:identifier>/markdown_documentation', methods=['GET'])
@auth_required
def load_markdown_documentation(identifier):
    """
    Relay to ontology server to retrieve the whole sos_trades models links diagram
    Object returned is a form of d3 js data structure

    Returned response is with the following data structure
        {
            Markdown_documentation:
                document: string,
            }
        }
    """

    user = session['user']
    app.logger.info(user)

    resp = make_response(jsonify(load_markdown_documentation_metadata(identifier)), 200)
    return resp


@app.route(f'/api/data/ontology/full_process_list', methods=['GET'])
@auth_required
def load_full_process_list():
    """
    Methods that retrieve all processes and related information

    Request object has no parameters

    Returned response is with the following data structure
            process_id:{
                uri:string,
                id:string,
                label: string,
                description: string,
                category: string,
                version: string,
                process_repository: string,
                quantity_disciplines_used:int,
                discipline_list:string list,
                associated_usecases: string list,
            }
        ]
    """

    user = session['user']
    app.logger.info(user)

    resp = make_response(jsonify(load_ontology_processes()), 200)
    return resp


@app.route(f'/api/data/ontology/general_information', methods=['GET'])
@auth_required
def load_general_information():
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

    user = session['user']
    app.logger.info(user)

    resp = make_response(jsonify(load_ontology_general_information()), 200)
    return resp
