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
from os.path import dirname, join

from dotenv import load_dotenv

if __name__ == '__main__':

    if os.environ.get('SOS_TRADES_SERVER_CONFIGURATION') is None:
        dotenv_path = join(dirname(__file__), '..', '..', '.flaskenv')
        load_dotenv(dotenv_path)

    # Import server module after a basic configuration in order to set
    # correctly server  executing environment
    from sos_trades_api.server.api_mode import api_v0_server

    api_v0_server.app.run(host='127.0.0.1', port='5004')
