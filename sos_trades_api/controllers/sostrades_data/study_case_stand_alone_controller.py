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

import json
import threading
from datetime import datetime
from os.path import join
from tempfile import gettempdir
from zipfile import ZipFile

from sos_trades_api.controllers.error_classes import InvalidFile, StudyCaseError
from sos_trades_api.controllers.sostrades_data.study_case_controller import (
    create_empty_study_case,
)
from sos_trades_api.models.database_models import StudyCase
from sos_trades_api.server.base_server import app
from sos_trades_api.tools.loading.study_case_manager import StudyCaseManager
from sos_trades_api.tools.study_management.study_management import (
    update_study_case_creation_status,
)


def get_study_stand_alone_zip(study_id):
    """
    export study read only and data in a zip file and return its path
    Args:
        study_id (int), id of the study to export
    """
    zip_file_path = None
    study_manager = StudyCaseManager(study_id)
    try:
        tmp_folder = gettempdir()
        file_name = f"zip_study_{study_manager.study.id}_{datetime.now().strftime('%d-%m-%Y-%H-%M-%S-%f')}.zip"
        zip_file_path = join(tmp_folder, file_name)
        if not study_manager.export_study_read_only_zip(zip_file_path):
            raise FileNotFoundError(f"Study {study_manager.study.name} has no read only to export")
           
    except Exception as error:
        raise InvalidFile(
            f"The following study file raised this error while trying to zip it : {error}")
    return zip_file_path

def create_study_stand_alone_from_zip(user_id, group_id, zip_file):
    # check the zip content
    # read metadata
    # create studyCase in db
    # unzip files in read only folder
    study_metadata = None
    # save zip_file in temporary folder
    tmp_folder = gettempdir()
    file_name = f"zip_study_{datetime.now().strftime('%d-%m-%Y-%H-%M-%S-%f')}.zip" 
    zip_file_path = join(tmp_folder, file_name)
    with open(zip_file_path, 'wb') as f:
        f.write(zip_file.read())

    with ZipFile(zip_file_path, 'r') as zfile:
        files_list = zfile.namelist()

        # read metadata file
        if "metadata.json" not in files_list:
            raise InvalidFile(
                "The Study Stand alone zip file is not valid : the metadata file is missing")
        
        with zfile.open("metadata.json") as metadata_file:

            try:
                metadata = json.load(metadata_file)
                study_metadata = StudyCaseManager.UnboundStudyCase()
                study_metadata.deserialize_standalone(metadata)
            except Exception as error:
                raise InvalidFile(
                    f"Error while reading the metadata of the study stand-alone zip: {str(error)}")
    if study_metadata is None:
        raise InvalidFile(
            "The Study Stand alone zip file is not valid : metadata not found")
            
    # create study case
    study_case = create_empty_study_case(user_id, study_metadata.name, study_metadata.repository,
                                            study_metadata.process, group_identifier=group_id, reference=None, from_type=StudyCase.FROM_STANDALONE,
                                            study_pod_flavor=None, execution_pod_flavor=None)
    
    # launch a thread that will write the zip files into the study folder
    threading.Thread(
                target=save_study_data_from_zip,
                args=(study_case.id, zip_file_path)).start()
    

    return study_case

def save_study_data_from_zip(study_case_id, zip_file_path:str):
    with app.app_context():
        update_study_case_creation_status(study_case_id, StudyCase.CREATION_IN_PROGRESS)

        study_case_manager = StudyCaseManager(study_case_id)
        try:
            # unzip all files
            with ZipFile(zip_file_path, 'r') as zfile:
                zfile.extractall(study_case_manager.dump_directory)
        except Exception as error:
            error_msg = f"Study Stand alone creation error: {str(error)}"
            update_study_case_creation_status(study_case_id, StudyCase.CREATION_ERROR, error_msg)
            raise StudyCaseError(error_msg)

        # check that needed files are present 
        if not study_case_manager.check_study_standalone_files():
            error_msg = "Study Stand alone creation error: study case zip doesn't contain all necessary study files"
            update_study_case_creation_status(study_case_id, StudyCase.CREATION_ERROR, error_msg)
            raise StudyCaseError(error_msg)
        
        update_study_case_creation_status(study_case_id, StudyCase.CREATION_DONE)





