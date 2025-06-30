'''
Copyright 2025 Capgemini

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
from flask import Blueprint, jsonify, make_response, request, session
from werkzeug.exceptions import BadRequest

from sos_trades_api.controllers.sostrades_data.ontology_controller import (
    load_markdown_documentation_metadata,
    load_ontology_usages,
)
from sos_trades_api.controllers.sostrades_data.study_case_controller import app

ontology_blueprint = Blueprint('ontology', __name__)

def init_ontology_routes(decorator):
    """
    Initialize ontology routes with a given decorator
    """
    @ontology_blueprint.route("/ontology-usages", methods=["POST"])
    @decorator
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
        data_request = request.json.get("ontology_request", None)

        missing_parameter = []
        if data_request is None:
            missing_parameter.append(
                "Missing mandatory parameter: ontology_request")

        if len(missing_parameter) > 0:
            raise BadRequest("\n".join(missing_parameter))

        resp = make_response(jsonify(load_ontology_usages(data_request)), 200)
        return resp


    @ontology_blueprint.route("/<string:identifier>/markdown_documentation", methods=["GET"])
    @decorator
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
        user = session["user"]
        app.logger.info(user)

        resp = make_response(jsonify(load_markdown_documentation_metadata(identifier)), 200)
        return resp
