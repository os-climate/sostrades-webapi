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
# Monkey patch eventlet before all imports
# Ignore checks, it HAS TO be made before imports
# ruff: noqa: E402
import eventlet

eventlet.monkey_patch()

# Set server name
import os

os.environ["SERVER_NAME"] = "MESSAGE_SERVER"

from flask_socketio import SocketIO

from sos_trades_api.server.base_server import app

# Initialize socket for messaging system
socketio = SocketIO()
socketio.init_app(app, cors_allowed_origins="*", async_mode="eventlet", async_handlers=True)

# load & register APIs
from sos_trades_api.routes.message import *
