'''
Copyright 2024 Capgemini

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
from flask import jsonify, make_response

from sos_trades_api.server.base_server import Config, app
from sos_trades_api.tools.authentication.authentication import auth_required
from sos_trades_api.tools.code_tools import extract_unit_from_flavor


@app.route("/api/data/flavors/study", methods=["GET"])
@auth_required
def get_flavors_config_study():
    """
    
    retrieve flavors from the configuration
    """
    flavor_from_config_dict = Config().kubernetes_flavor_config_for_study
    flavor_dict = None
    if flavor_from_config_dict is not None:
        flavor_dict = extract_unit_from_flavor(flavor_from_config_dict)
    return make_response(jsonify(flavor_dict), 200)

@app.route("/api/data/flavors/exec", methods=["GET"])
@auth_required
def get_flavors_config_exec():
    """
    
    retrieve flavors from the configuration
    """
    flavor_from_config_dict = Config().kubernetes_flavor_config_for_exec
    flavor_dict = None
    if flavor_from_config_dict is not None:
        flavor_dict = extract_unit_from_flavor(flavor_from_config_dict)
    return make_response(jsonify(flavor_dict), 200)
