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


@app.route("/api/data/flavors/study", methods=["GET"])
@auth_required
def get_flavors_config_study():
    """
    
    retrieve flavors from the configuration
    """
    flavor_dict = Config().kubernetes_flavor_config_for_study
    all_flavor_names = []
    if flavor_dict is not None:
        all_flavor_names = list(flavor_dict.keys())
    return make_response(jsonify(all_flavor_names), 200)

@app.route("/api/data/flavors/exec", methods=["GET"])
@auth_required
def get_flavors_config_exec():
    """
    
    retrieve flavors from the configuration
    """
    flavor_dict = Config().kubernetes_flavor_config_for_exec
    all_flavor_names = []
    if flavor_dict is not None:
        all_flavor_names = list(flavor_dict.keys())
    return make_response(jsonify(all_flavor_names), 200)
