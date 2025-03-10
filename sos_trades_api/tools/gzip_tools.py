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
import gzip
import io
import json
from typing import Any

from flask import Response

from sos_trades_api.models.custom_json_encoder import CustomJsonEncoder
from sos_trades_api.server.base_server import app
from sos_trades_api.tools.code_tools import time_function


@time_function(app.logger)
def make_gzipped_response(obj:Any):
    """
    Generates a gzipped json response from an object
    """
    json_data = json.dumps(obj, cls=CustomJsonEncoder)
    gzip_buffer = io.BytesIO()
    
    with gzip.GzipFile(mode='w', fileobj=gzip_buffer) as gz:
        gz.write(json_data.encode('utf-8'))
    
    response = Response(gzip_buffer.getvalue(), content_type='application/json')
    response.headers['Content-Encoding'] = 'gzip'
    response.headers['Content-Length'] = len(gzip_buffer.getvalue())
    return response
