'''
Copyright 2022 Airbus SAS

Modifications on 25/03/2024 Copyright 2024 Capgemini
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

os.environ["SERVER_NAME"] = "DATA_SERVER"

from sos_trades_api.server import base_server

app = base_server.app
db = base_server.db

from sos_trades_api.server.base_server import check_identity_provider_availability

check_identity_provider_availability()

config = base_server.config

# if config.execution_strategy == config.CONFIG_EXECUTION_STRATEGY_K8S or \
#     config.server_mode == config.CONFIG_SERVER_MODE_K8S:
#     launch_thread_update_pod_allocation_status()

# load & register APIs
from sos_trades_api.routes.data import *
