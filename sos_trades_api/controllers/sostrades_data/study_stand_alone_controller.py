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

from shutil import copy, make_archive
import threading
from os.path import join, exists
from sos_trades_api.server.base_server import app, db
from sos_trades_api.models.database_models import StudyStandAloneStatus
from sos_trades_api.tools.loading.study_case_manager import StudyCaseManager
from sostrades_core.tools.folder_operations import makedirs_safe, rmtree_safe
from sostrades_core.tools.tree.serializer import DataSerializer

def get_export_zip_file_name(study_case_id):
    return f"study_{study_case_id}_stand_alone"

def get_status_export_study_stand_alone(study_case_id:int)->StudyStandAloneStatus:
    """
    Get the status of the export of a study in stand alone
    
    :param study_case_id: identifier of the study case to be exported
    :type study_case_id: int
    """

    # load the status if exists:
    status = None
    status_query = StudyStandAloneStatus.query.filter(StudyStandAloneStatus.study_case_id == study_case_id).all()
    if len(status_query) > 0:
        status = status_query[0]
    
    if status is not None:
        if status.is_finished:
            # check if the file exists
            study_manager = StudyCaseManager(study_case_id)
            zip_file_path = join(study_manager.dump_directory, get_export_zip_file_name(study_case_id))
            if not exists(zip_file_path):
                status.is_in_error = True
                status.is_finished = False
                status.error_message= "No exported file found."
        else:
            #check if thread is still alive
            all_threads = threading.enumerate()
            current_thread = [thread for thread in all_threads if thread.getName() == str(study_case_id)]
            if len(current_thread) == 0:
                status.is_in_error = True
                status.error_message= "No exported file found."

    return status

def start_export_study_stand_alone(study_case_id:int)->StudyStandAloneStatus:
    """
    Start the export of a study in stand alone:
        -> launch the thread that will create the study zip file

    :param study_case_id: identifier of the study case to be exported
    :type study_case_id: int
    """

    # load the status if exists:
    status = None
    status_query = StudyStandAloneStatus.query.filter(StudyStandAloneStatus.study_case_id == study_case_id).all()
    if len(status_query) > 0:
        status = status_query[0]
    else:
        status = StudyStandAloneStatus()

    # reset the status data
    status.error_message = ""
    status.is_finished = False
    status.is_in_error = False
    status.progress = 0
    status.next_progress = 0
    status.progress_text = "Waiting to that the export process"

    db.session.add(status)
    db.session.commit()

    # start the process
    thread = threading.Thread(target=export_study_stand_alone,args=(study_case_id))
    thread.setName(str(study_case_id))
    thread.start()

    return status

def export_study_stand_alone(study_case_id):
    """
    build the .zip folder 
    """
    #retrieve the status
    with app.app_context():
        try:
            update_progress(study_case_id, 0, 100, "Start creating zip file")

            #get the study manager
            study_manager = StudyCaseManager(study_case_id)

            #check that there is a read only mode
            if study_manager.check_study_case_json_file_exists():
                root_folder = study_manager.dump_directory
                export_name =  get_export_zip_file_name(study_case_id)
                export_folder = join(root_folder,export_name)
                
                #TODO:export ontology

                #TODO: export documentation

                # create a folder to copy all data in it
                if not export_folder.is_dir():
                    makedirs_safe(export_folder)
                update_progress(study_case_id, 10, 70, "Export folder created")

                # copy files in it
                # copy read only file
                copy(root_folder.joinpath(StudyCaseManager.LOADED_STUDY_FILE_NAME),
                     export_folder.joinpath(StudyCaseManager.LOADED_STUDY_FILE_NAME))
                update_progress(study_case_id, 50, 70, "Read only file exported")

                # copy pkl file
                copy(root_folder.joinpath(DataSerializer.pkl_filename),
                     export_folder.joinpath(DataSerializer.pkl_filename))
                update_progress(study_case_id, 70, 100, "Data file exported. Creating zip file...")

                # zip folder and return zip filepath
                make_archive(export_folder, "zip", root_folder, export_name)
                rmtree_safe(export_folder)
                update_progress(study_case_id, 100, 100, "Zip file done", True)

            else:
                set_error_status(study_case_id, f'error while exporting study {study_case_id}: A read only file is needed')
        except Exception as ex:
            set_error_status(study_case_id,f'error while exporting study {study_case_id}: {str(ex)}')
        

def update_progress(study_case_id:int, progress:int, next_progress:int, progress_text:str, is_finished:bool=False):
    status = None
    status_query = StudyStandAloneStatus.query.filter(StudyStandAloneStatus.study_case_id == study_case_id).all()
    if len(status_query) > 0:
        status = status_query[0]
    else:
        status = StudyStandAloneStatus()

    # reset the status data
    status.error_message = ""
    status.is_finished = is_finished
    status.is_in_error = False
    status.progress = progress
    status.next_progress = next_progress
    status.progress_text = progress_text

    db.session.add(status)
    db.session.commit()

def set_error_status(study_case_id:int, error_message:int):
    status = None
    status_query = StudyStandAloneStatus.query.filter(StudyStandAloneStatus.study_case_id == study_case_id).all()
    if len(status_query) > 0:
        status = status_query[0]
    else:
        status = StudyStandAloneStatus()

    # reset the status data
    status.error_message = error_message
    status.is_finished = False
    status.is_in_error = True
    
    db.session.add(status)
    db.session.commit()

