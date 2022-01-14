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
# coding: utf-8
import os
import time
import sys
import tempfile
import argparse
import logging
from os.path import join, dirname
from os import stat
from datetime import datetime, timezone
from dotenv import load_dotenv

if __name__ == '__main__':

    if os.environ.get('SOS_TRADES_SERVER_CONFIGURATION') is None:
        dotenv_path = join(dirname(__file__), '.flaskenv')
        load_dotenv(dotenv_path)

    # Import server module after a basic configuration in order to set
    # correctly server  executing envrionnement
    from sos_trades_api import message_server
    from sos_trades_api.config import Config
    from sos_trades_api.base_server import PRODUCTION
    config = Config()

    # For development purpose assign envrionnement variable
    if os.environ['FLASK_ENV'] != PRODUCTION:

        if os.environ.get(config.execution_strategy_env_var) is None:
            if sys.platform == "win32":
                os.environ[config.execution_strategy_env_var] = 'subprocess'
            else:
                os.environ[config.execution_strategy_env_var] = 'subprocess'
            message_server.app.logger.info(
                f'value not found environment variable {config.execution_strategy_env_var}. Set it to default: {os.environ[config.execution_strategy_env_var]}')
        else:
            message_server.app.logger.info(
                f'value found environment variable {config.execution_strategy_env_var}: {os.environ[config.execution_strategy_env_var]}')

    # - Consistency check on server environment (every variables must be provided)
    if os.environ['FLASK_ENV'] == PRODUCTION:
        config.check()

    message_server.socketio.run(message_server.app, host='0.0.0.0', port=5002)
