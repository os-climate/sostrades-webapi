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
"""
mode: python; py-indent-offset: 4; tab-width: 4; coding: utf-8
api version methods
"""

# pylint: disable=line-too-long

from os import environ
from os.path import join, dirname, exists
from datetime import datetime
import sos_trades_api
from sos_trades_api.server.base_server import app


def application_version():
    """Methods that build the API version
    Version is retrieve throught a version.info file located in the project directory or generated if not
    (generated one will be suffixed by a star '*'

    :return: string with version (DD.MM.YY format)
    """

    version = f'{datetime.now().strftime("%d.%m.%Y")}*'

    if environ.get('FLASK_ENV') is None or environ['FLASK_ENV'] == 'development':
        return version

    try:
        path = join(dirname(sos_trades_api.__file__), 'version.info')

        if exists(path):
            version = open(path).read().strip()
        else:  # file does not exist so, generated one
            with open(path, 'w') as file_handler:
                file_handler.write(version)
                file_handler.close()
    except:
        app.logger.exception(
            'The following error occurs when trying to get the version')

    return version
