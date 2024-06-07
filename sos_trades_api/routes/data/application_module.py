'''
Copyright 2022 Airbus SAS
Modifications on 2023/11/08-2023/11/09 Copyright 2023 Capgemini

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
from flask import make_response
from flask.json import jsonify

from sos_trades_api.server.base_server import app
from sos_trades_api.tools.api_version import application_version
from sos_trades_api.tools.authentication.authentication import auth_required

"""
Application module
"""

@app.route('/api/data/application/infos', methods=['GET'])
def application_info():
    """
    application info
    """
    result = {}
    result['version'] = application_version()
    result['platform'] = app.config['SOS_TRADES_ENVIRONMENT']
    resp = make_response(jsonify(result), 200)
    return resp


@app.route('/api/data/application/support', methods=['GET'])
@auth_required
def application_support():
    """
    application support
    """
    result = {'support': 'contact@sostrades.org'}
    resp = make_response(jsonify(result), 200)
    return resp