'''
Copyright 2022 Airbus SAS
Modifications on 2024/06/07 Copyright 2024 Capgemini
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
from flask import jsonify, make_response, session

from sos_trades_api.controllers.sostrades_data.ontology_controller import (
    load_models,
    load_models_status_filtered,
    load_ontology_general_information,
    load_ontology_processes,
    load_parameter_label_list,
    load_parameters,
)
from sos_trades_api.server.base_server import app
from sos_trades_api.tools.authentication.authentication import (
    auth_required,
    get_authenticated_user,
)
from sos_trades_api.tools.right_management.functional.process_access_right import (
    ProcessAccess,
)


@app.route("/api/data/ontology/models/status", methods=["GET"])
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

    resp = make_response(jsonify(load_models_status_filtered(process_access.user_process_list)))

    return resp


@app.route("/api/data/ontology/full_models_list", methods=["GET"])
@auth_required
def load_ontology_full_model_list():
    """
    Method that return a list of all ontology disciplines and their related information
    Returned response is with the following data structure
       [
           discipline_id:{
               'id': string,
               'uri': string,
               'label': string,
               'definition': string,
               'category': string,
               'version': string,
               'last_modification_date': string,
               'source': string,
               'validated_by': string,
               'python_class': string,
               'validated': string,
               'icon': string,
               'output_parameters_quantity': int,
               'input_parameters_quantity': int,
               'class_inheritance': string list,
               'code_repository': string,
               'type': string,
               'python_module_path': string,
               'output_parameters': [{parameter_usage_id: string, parameter_id: string, parameter_label: string}],
               'input_parameters': [{parameter_usage_id: string, parameter_id: string, parameter_label: string}],
               'process_using_discipline': [{process_id: string, process_label: string, repository_id: string, repository_label: string}],
           }
       ]
    """
    user = get_authenticated_user()
    app.logger.info(user)

    models = load_models()
    resp = make_response(jsonify(models))

    return resp


@app.route("/api/data/ontology/full_parameter_list", methods=["GET"])
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


@app.route("/api/data/ontology/full_parameter_label_list", methods=["GET"])
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



@app.route("/api/data/ontology/full_process_list", methods=["GET"])
@auth_required
def load_full_process_list():
    """
    Methods that retrieve all processes and related information

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
    user = session["user"]
    app.logger.info(user)

    resp = make_response(jsonify(load_ontology_processes()), 200)
    return resp


@app.route("/api/data/ontology/general_information", methods=["GET"])
@auth_required
def load_general_information():
    """
    Methods returning generic information concerning the current ontology

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
    user = session["user"]
    app.logger.info(user)

    resp = make_response(jsonify(load_ontology_general_information()), 200)
    return resp
