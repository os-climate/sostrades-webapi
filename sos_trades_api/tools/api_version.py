'''
Copyright 2022 Airbus SAS
Modifications on 08/12/2023 Copyright 2023 Capgemini
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

from datetime import datetime
from os import environ
from os.path import dirname, exists, join
import json

import sos_trades_api
from sos_trades_api.server.base_server import app

"""
api version methods
"""

def application_version():
    """
    Methods that build the API version
    Version is retrieve throught a version.info file located in the project directory or generated if not
    (generated one will be suffixed by a star '*'

    :return: string with version (DD.MM.YY* format or free string format))
    """
    #version = f'{datetime.now().strftime("%d.%m.%Y")}*'

    version = "Version not available"

    if environ.get("FLASK_ENV") is None or environ["FLASK_ENV"] == "development":
        return f'{datetime.now().strftime("%d.%m.%Y")}*' # id dev always give the last date

    try:
        path = join(dirname(sos_trades_api.__file__), "version.info")

        if exists(path):
            version = open(path).read().strip()
        # remove the file creation since version.info is now generated with devops
        #else:  # file does not exist so, generated one
        #    with open(path, 'w') as file_handler:
        #        file_handler.write(version)
        #        file_handler.close()
    except:
        app.logger.exception(
            "The following error occurs when trying to get the version")

    return version

def git_commits_info():
    """
    Methods that retrieve all the repositories used by the platform last commits info
    This info is in the following file:
    git_commits_info_file_path = f"{platform_path}/sostrades-webapi/sos_trades_api/git_commits_info.json"
    """

    git_data = None
    git_commits_info_file_path = join(dirname(sos_trades_api.__file__), "git_commits_info.json")
    if exists(git_commits_info_file_path):
        with open(git_commits_info_file_path, 'r') as json_file:
            git_data = json.load(json_file)
    return git_data