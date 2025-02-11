'''
Copyright 2022 Airbus SAS
Modifications on 2023/10/02-2023/11/03 Copyright 2023 Capgemini

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
import argparse
# coding: utf-8
import os
from os.path import dirname, join

from dotenv import load_dotenv

def parse_arguments():
    # Create an argument parser
    parser = argparse.ArgumentParser()

    # Add --debug flag, default is False
    parser.add_argument('--debug', action='store_true', help="Enable debugging")

    # Parse the arguments
    args = parser.parse_args()

    return args

if __name__ == "__main__":

    if os.environ.get("SOS_TRADES_SERVER_CONFIGURATION") is None:
        dotenv_path = join(dirname(__file__), "..", "..", ".flaskenv")
        load_dotenv(dotenv_path)

    # Import server module after a basic configuration in order to set
    # correctly server executing environment
    from sos_trades_api.server.split_mode import data_server

    data_server.app.run(host="0.0.0.0", port="8001", debug=parse_arguments().debug)
