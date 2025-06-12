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
import os
from os.path import basename, exists, join
from shutil import copy

from sostrades_core.tools.folder_operations import makedirs_safe, rmtree_safe

from sos_trades_api.tools.file_stream.file_stream import verify_files_after_copy
from sos_trades_api.tools.file_tools import (
    read_object_in_json_file,
    write_object_in_json_file,
)


class StudyReadOnlyRWHelper():
    """
    Class to define how and where is written the read only mode of a study
    """
    LOADED_STUDY_FILE_NAME = "loaded_study_case.json"
    READ_ONLY_FOLDER_NAME = "read_only_study"
    RESTRICTED_STUDY_FILE_NAME = "loaded_study_case_no_data.json"
    DASHBOARD_FILE_NAME = "dashboard.json"
    ONTOLOGY_FILE_NAME = "ontology.json"
    DOCUMENTATION_FOLDER_NAME = "documentation"

    def __init__(self, dump_directory):
        self.__dump_directory = dump_directory
        self.__read_only_folder_path = join(self.__dump_directory, self.READ_ONLY_FOLDER_NAME)
        self.__read_only_file_path = join(self.__read_only_folder_path, self.LOADED_STUDY_FILE_NAME)
        self.__read_only_file_nodata_path = join(self.__read_only_folder_path, self.RESTRICTED_STUDY_FILE_NAME)
        self.__documentation_folder_path = join(self.__read_only_folder_path, self.DOCUMENTATION_FOLDER_NAME)
        self.__ontology_file_path = join(self.__read_only_folder_path, self.ONTOLOGY_FILE_NAME)
        self.__dashboard_file_path = join(self.__read_only_folder_path, self.DASHBOARD_FILE_NAME)

    @property
    def read_only_folder_path(self):
        return self.__read_only_folder_path

    @property
    def read_only_exists(self):
        return exists(self.__read_only_file_path)
    
    @property
    def ontology_files_exists(self):
        return exists(self.__ontology_file_path) and exists(self.__documentation_folder_path)

    @property
    def dashboard_file_exists(self):
        return exists(self.__dashboard_file_path)

    def __write_object_in_read_only_folder(self, object, file_path) -> str:
        """
        Return the read only foler of the study, 
        if the folder doesn't exists it is created
        """
        makedirs_safe(self.__read_only_folder_path, exist_ok=True)
        return write_object_in_json_file(object, file_path)
    
    def get_read_only_file_path(self, no_data=False):
        """
        Return the read only mode file path
        :param no_data: if true, return the path to the reastricted viewer file instead of the read only file
        :type no_data: bool
        """
        if no_data:
            return self.__read_only_file_nodata_path
        else:
            return self.__read_only_file_path

    def get_dashboard_file_path(self):
        """
        Return the dashboard file path
        """
        return self.__dashboard_file_path
    
    def write_study_case_in_read_only_file(self, loaded_study, no_data=False):
        """
        Save study case loaded into json file for read only mode
        Args:
            loaded_study (LoadedStudyCase): loaded_study_case to save
        Return True if the write succeeded
        """
        return self.__write_object_in_read_only_folder(loaded_study, self.get_read_only_file_path(no_data))
    

    def read_study_case_in_read_only_file(self, no_data=False):
        """
        Read study case loaded into json file for read only mode
        Args:
            no_data (bool): if data reading rights
        Return:
            json read only file content
        """
        read_only = None
        if self.read_only_exists:
            read_only = read_object_in_json_file(self.get_read_only_file_path(no_data))
        
        return read_only
    
    def write_dashboard(self, dashboard_data):
        """
        save dashboard data in a json file named dashboard.json
        Args:
             dashboard_data (dict): dashboard data in json format

        Return:
            True if the write succeeded
        """
        return self.__write_object_in_read_only_folder(dashboard_data, self.__dashboard_file_path)

    def read_dashboard(self):
        """
        get content of the dashboard saved file if exists, return None if not
        Return:
            Dashboard file content
        """
        dashboard_data = None
        if exists(self.__dashboard_file_path):
            dashboard_data = read_object_in_json_file(self.__dashboard_file_path)
        
        return dashboard_data

    def write_ontology(self, ontology_data):
        """
        save ontology data in a json file named ontology.json
        Args:
            ontology_data (dict): ontology data in json format
        Return:
            True if the write succeeded
        """
        return self.__write_object_in_read_only_folder(ontology_data, self.__ontology_file_path)

    def read_ontology(self):
        """
        get content of the ontology saved file if exists, return None if not
        Return:
            Ontology file content
        """
        ontology_data = None
        if exists(self.__ontology_file_path):
            ontology_data = read_object_in_json_file(self.__ontology_file_path)
        
        return ontology_data
    

    def write_documentations(self, documentation_data_dict):
        """
        save documentations in the documentation folder, each documentation written in a .md file
        Args:
            documentation_data_dict: dict[documentation_name, documentation_data]
        Return:
            True if the write succeeded
        """
        makedirs_safe(self.__documentation_folder_path, exist_ok=True)

        for doc_name, doc in documentation_data_dict.items():
            with open(join(self.__documentation_folder_path, f'{doc_name}.md'), "w+", encoding='utf-8') as md_file:
                md_file.writelines(doc)

    def read_documentation(self, documentation_name):
        """
        get content of the documentation md saved file if exists, return None if not
        Return:
            documentation file content
        """
        documentation_data = None
        documentation_file_path = join(self.__documentation_folder_path, f'{documentation_name}.md')
        if exists(documentation_file_path):
            with open(documentation_file_path, "r") as md_file:
                    documentation_data = md_file.read()
        
        return documentation_data
    
    def copy_file_in_read_only_folder(self, file_path:str):
        """
        Copy a file into the read only folder
        Args:
            file_path (str): path of the file to copy
        """
        if not exists(file_path):
            return
        file_name = basename(file_path)
        copy(file_path, join(self.__read_only_folder_path, file_name))

    def delete_read_only_mode(self):
        """
        Delete the read only foler containing all read only files
        """
        if not exists(self.__read_only_folder_path):
            return
        
        rmtree_safe(self.__read_only_folder_path)
            

    def migrate_to_new_read_only_folder(self):
        """
        function that copy all existing read only files into the read only folder, 
        check the copied file and then delete removed files
        Return:
            (list[str]) migrations errors, empty if all succeeded
        """
        list_files = [self.LOADED_STUDY_FILE_NAME, 
                      self.RESTRICTED_STUDY_FILE_NAME,
                      self.ONTOLOGY_FILE_NAME,
                      self.DASHBOARD_FILE_NAME]
        migration_errors = []
        for file_name in list_files:
            file_to_copy_path = join(self.__dump_directory, file_name)
            if not exists(file_to_copy_path):
                continue

            makedirs_safe(self.__read_only_folder_path, exist_ok=True)
            new_file_path = join(self.__read_only_folder_path, file_name)

            try:
                copy(file_to_copy_path, new_file_path)
                # check the created file
                if not verify_files_after_copy(file_to_copy_path, new_file_path):
                    migration_errors.append(f'Check of {file_to_copy_path} and {new_file_path} invalid\n')
            except Exception as error:
                migration_errors.append(f'Error while copying of {file_to_copy_path}: {str(error)}\n')
        
        # copy documentation folder
        folder_to_copy_path = join(self.__dump_directory, self.DOCUMENTATION_FOLDER_NAME)
        new_folder_path = join(self.__read_only_folder_path, self.DOCUMENTATION_FOLDER_NAME)
        if exists(folder_to_copy_path):           
            try:
                makedirs_safe(new_folder_path, exist_ok=True)
                # check the created files
                for file in os.scandir(folder_to_copy_path):
                    new_file_path = join(new_folder_path, file.name)
                    copy(file.path, new_folder_path)
                    if not verify_files_after_copy(file.path, new_file_path):
                        migration_errors.append(f'Check of {file.path} and {new_file_path} invalid\n')
            except Exception as error:
                migration_errors.append(f'Error while copying of {folder_to_copy_path}: {str(error)}\n')

        # if there is errors, stop the process now
        if len(migration_errors) > 0:
            return migration_errors
        
        # else delete old files
        current_deleting = ''
        try:
            # delete read only files
            for file_name in list_files:
                file_to_copy_path = join(self.__dump_directory, file_name)
                current_deleting = file_to_copy_path
                if exists(file_to_copy_path):
                    os.remove(file_to_copy_path)
                # check if backup file exists and delete it
                file_and_extension = file_name.split(".")
                backup_file_path = join(self.__dump_directory, 
                    file_and_extension[0]
                    + '_backup.'
                    + file_and_extension[1]
                )
                current_deleting = backup_file_path
                if exists(backup_file_path):
                    os.remove(backup_file_path)
            # delete documentation folder
            current_deleting = folder_to_copy_path
            if exists(folder_to_copy_path):
                rmtree_safe(folder_to_copy_path)
        except Exception as error:
            migration_errors.append(f'Error while deletion of {current_deleting}: {str(error)}\n')

        return migration_errors
            
        



