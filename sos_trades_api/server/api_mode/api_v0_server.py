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
# Set server name
import os


os.environ["SERVER_NAME"] = "API_V0_SERVER"
os.environ["SOS_TRADES_SERVER_MODE"] = "mono"

from sos_trades_api import __file__
from sos_trades_api.server import base_server

app = base_server.app
db = base_server.db

# register templates
app.template_folder = os.path.join(
    os.path.dirname(__file__),
    "templates",
    "api_v0",
)

# load & register APIs
# register blueprints
from sos_trades_api.blueprints.ontology.ontology_blueprint import (
    init_ontology_routes,
    ontology_blueprint,
)
from sos_trades_api.tools.authentication.authentication import api_key_required

from sos_trades_api.blueprints.study_case.read_only_blueprint import (read_only_blueprint,
    init_read_only_routes,
)

init_ontology_routes(api_key_required)
app.register_blueprint(ontology_blueprint, url_prefix="/api/v0/ontology")

init_read_only_routes(api_key_required)
app.register_blueprint(read_only_blueprint, url_prefix="/api/v0/study-case")

from sos_trades_api.routes.api_v0 import *

