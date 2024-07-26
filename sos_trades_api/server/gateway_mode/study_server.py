'''
Copyright 2022 Airbus SAS

Modifications on 29/04/2024 Copyright 2024 Capgemini
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
from datetime import datetime
import os
import re

os.environ["SERVER_NAME"] = "STUDY_SERVER"

from sos_trades_api.server import base_server

app = base_server.app
db = base_server.db



# load & register APIs
from sos_trades_api.routes.main import *
from sos_trades_api.routes.post_processing import *

def get_study_id_for_study_server():
    '''
    If the pod is a study server, find the study ID:
    The study server has a HOSTNAME named sostrades-study-server-[study_id]
    :return: study id (int) (None if the study server is not )
    '''
    study_id = None
    pod_name =os.environ.get("HOSTNAME", "")
    if pod_name.startswith("sostrades-study-server-"):
        #retreive study id
        match = re.search(r"(?<=sostrades-study-server-)\d+", pod_name)
        if match:
            #the number represents the study id
            study_id = int(match.group(0))
        else:
            exception_message = f"Could not find the study ID in the pod environment variable HOSTNAME={pod_name}"
            app.logger.exception(exception_message)
            raise Exception(exception_message)
    return study_id


def load_specific_study(study_identifier):
    """
    Load a specific study.
    Generally used when a specific study is launched to manage an unique study at startup
    :param study_identifier: database identifier of the study to load
    :type study_identifier: integer

    """
    from sos_trades_api.controllers.sostrades_main.study_case_controller import (
        load_or_create_study_case,
    )

    load_or_create_study_case(
        user_id=None, 
        study_case_identifier=study_identifier,
        study_access_right=None,
        read_only_mode=False)
        
# in case of study server, find the study server ID
study_id = get_study_id_for_study_server()
if study_id is not None:
    # in case of study server, save the active study file and load the study
    from sos_trades_api.config import Config
    from sos_trades_api.tools.active_study_management.active_study_management import (
        ACTIVE_STUDY_FILE_NAME,
        save_study_last_active_date,
    )
    
    # create the active study file if it doesn't exist
    local_path = Config().local_folder_path
    if local_path != "" and os.path.exists(local_path):
        file_path = os.path.join(local_path, f"{ACTIVE_STUDY_FILE_NAME}{study_id}.txt")
        if not os.path.exists(file_path):
            save_study_last_active_date(study_id, datetime.now())
    
    # then load the study
    load_specific_study(study_id)