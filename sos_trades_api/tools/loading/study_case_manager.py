'''
Copyright 2022 Airbus SAS
Modifications on 2023/05/12-2023/11/09 Copyright 2023 Capgemini

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
import logging
import os
from os.path import join
from pathlib import Path
from shutil import copy

from eventlet import sleep
from sostrades_core.execution_engine.proxy_discipline import ProxyDiscipline
from sostrades_core.study_manager.base_study_manager import BaseStudyManager
from sostrades_core.tools.dashboard.dashboard_factory import generate_dashboard
from sostrades_core.tools.rw.load_dump_dm_data import CryptedLoadDump, DirectLoadDump
from sostrades_core.tools.tree.serializer import DataSerializer

from sos_trades_api.config import Config
from sos_trades_api.controllers.sostrades_data.ontology_controller import (
    load_markdown_documentation_metadata,
    load_n2_matrix,
    load_ontology_usages,
    load_processes_metadata,
    load_repositories_metadata,
)
from sos_trades_api.models.database_models import (
    AccessRights,
    Group,
    StudyCase,
    StudyCaseAccessGroup,
    StudyCaseExecution,
)
from sos_trades_api.models.loaded_study_case import LoadedStudyCase, LoadStatus
from sos_trades_api.server.base_server import app, db
from sos_trades_api.tools.gzip_tools import zip_files_and_folders
from sos_trades_api.tools.loading.loaded_tree_node import get_treenode_ontology_data
from sos_trades_api.tools.loading.study_read_only_rw_manager import (
    StudyReadOnlyRWHelper,
)
from sos_trades_api.tools.logger.study_case_sqlalchemy_handler import (
    StudyCaseSQLAlchemyHandler,
)
from sos_trades_api.tools.visualisation.couplings_force_graph import (
    get_couplings_force_graph,
)
from sos_trades_api.tools.visualisation.execution_workflow_graph import (
    SoSExecutionWorkflow,
)
from sos_trades_api.tools.visualisation.interface_diagram import (
    InterfaceDiagramGenerator,
)

"""
Implementation of abstract class AbstractStudyManager to manage study from object use into the WEBAPI
"""

class StudyCaseError(Exception):
    """Base StudyCase Exception"""

    def __init__(self, msg=None):
        Exception.__init__(self, msg)

    def __str__(self):
        return self.__class__.__name__ + "(" + Exception.__str__(self) + ")"


class InvalidProcess(StudyCaseError):
    """Invalid process (Raise an error while trying to load it)"""


class InvalidStudy(StudyCaseError):
    """Invalid study"""


class StudyCaseManager(BaseStudyManager):
    BACKUP_FILE_NAME = "_backup"
    
    class UnboundStudyCase:
        """
        Class that manage a study case object without being linked to sqlalchemy session
        """

        def __init__(self):
            """
            Constructor
            """
            self.id = None
            self.group_id = None
            self.name = None
            self.repository = None
            self.process = None
            self.process_id = None
            self.description = None
            self.creation_date = None
            self.creation_status = None
            self.reference = None
            self.from_type = None
            self.modification_date = None
            self.user_id_execution_authorised = None
            self.current_execution_id = None
            self.error = None
            self.disabled = None
            self.study_pod_flavor = None
            self.execution_pod_flavor = None
            self.is_stand_alone = False

        def init_from_study_case(self, study_case: StudyCase):
            """
            Initialize current instance with data coming from a StudyCase instance

            :param study_case: study case instance from which data will be copied
            :type study_case:  sos_trades_api.models.database_models.StudyCase
            """
            self.id = study_case.id
            self.group_id = study_case.group_id
            self.name = study_case.name
            self.repository = study_case.repository
            self.process = study_case.process
            self.process_id = study_case.process_id
            self.description = study_case.description
            self.creation_date = study_case.creation_date
            self.creation_status = study_case.creation_status
            self.reference = study_case.reference
            self.from_type = study_case.from_type
            self.modification_date = study_case.modification_date
            self.user_id_execution_authorised = study_case.user_id_execution_authorised
            self.current_execution_id = study_case.current_execution_id
            self.error = study_case.error
            self.disabled = study_case.disabled
            self.study_pod_flavor = study_case.study_pod_flavor
            self.execution_pod_flavor = study_case.execution_pod_flavor
            self.is_stand_alone = study_case.is_stand_alone
        
        def serialize_standalone(self):
            """
            json serializer for study in stand-alone purpose
            """
            return {
                "name": self.name,
                "repository": self.repository,
                "process": self.process,
                "description": self.description
            }
        
        def deserialize_standalone(self, json_data):
            """
            json deserializer for study in stand-alone purpose
            """
            self.name = json_data["name"]
            self.repository = json_data["repository"]
            self.process = json_data["process"]
            self.description = json_data["description"]

    def __init__(self, study_identifier):
        """
        Constructor

        :param study_identifier: database study identifier
        :type study_identifier: int

        """
        self.__study_identifier = study_identifier
        self.__study = None

        self.__load_study_case_from_identifier()

        self.__rw_strategy = None
        self.__get_read_write_strategy()


        self.__root_dir = self.get_root_study_data_folder(
            self.__study.group_id, self.__study.id,
        )

        super().__init__(
            self.__study.repository,
            self.__study.process,
            self.__study.name,
            self.__root_dir,
            yield_method=sleep,
            logger=logging.getLogger(f"{self.__study_identifier}.sostrades_core.ExecutionEngine"),
        )

        self.__study_database_logger = None

        self.load_status = LoadStatus.NONE

        # loading status in case of dataset import
        self.dataset_load_status = LoadStatus.NONE
        self.dataset_load_error = None

        # export status in case of dataset export
        # it is a dict with notification id in case multiple export at the same time
        self.dataset_export_status_dict = {}
        self.dataset_export_error_dict = {}

        self.n2_diagram = {}
        self.__error_message = ""

        self.__read_only_rw_strategy = StudyReadOnlyRWHelper(self.dump_directory)

    @property
    def study(self) -> StudyCase:
        """
        Return the current Study object
        """
        return self.__study

    @property
    def study_database_logger(self) -> StudyCaseSQLAlchemyHandler:
        """
        Return the current database logger handler used by the study
        """
        return self.__study_database_logger

    @property
    def error_message(self) -> str:
        """
        Return the current error message
        """
        return self.__error_message

    def _init_exec_engine(self):
        """
        Overloaded method that initialize execution engine instance
        """
        super()._init_exec_engine()

    def raw_log_file_path_absolute(
        self, specific_study_case_execution_identifier=None,
    ) -> str:
        """
        Build the raw log file path of the study

        :param specific_study_case_execution_identifier: Optional, to retrieve execution which is not the current one in
        the study case
        :type specific_study_case_execution_identifier: str/int
        """
        file_path = ""

        if self.__study is not None:
            
            if self.__study.is_stand_alone:
                # find the execution log file in the read only folder with names that ends with "-execution.log" 
               for file in os.listdir(self.__read_only_rw_strategy.read_only_folder_path):
                    if file.endswith("-execution.log"):
                        file_path = os.path.join(self.__read_only_rw_strategy.read_only_folder_path, file)
                        break
            else:
                study_execution_identifier = self.__study.current_execution_id
                if specific_study_case_execution_identifier is not None:
                    study_execution_identifier = specific_study_case_execution_identifier

                file_path = os.path.join(
                    self.dump_directory,
                    f"sc{self.__study.id}-sce{study_execution_identifier}-execution.log",
                )

        return file_path

    def raw_log_file_path_relative(
        self, specific_study_case_execution_identifier=None,
    ) -> str:
        """
        Build the raw log file path of the study

        :param specific_study_case_execution_identifier: Optional, to retrieve execution which is not the current one in
        the study case
        """
        file_path = ""

        if self.__study is not None:
            if self.__study.is_stand_alone:
                # find the execution log file in the read only folder with names that ends with "-execution.log" 
               for file in os.listdir(self.__read_only_rw_strategy.read_only_folder_path):
                    if file.endswith("-execution.log"):
                        file_path = os.path.join(
                            str(self.__study.group_id),
                            str(self.__study.id),
                            self.__read_only_rw_strategy.READ_ONLY_FOLDER_NAME,
                            file)
                        break
            else:
                study_execution_identifier = self.__study.current_execution_id
                if specific_study_case_execution_identifier is not None:
                    study_execution_identifier = specific_study_case_execution_identifier

                file_path = os.path.join(
                    str(self.__study.group_id),
                    str(self.__study.id),
                    f"sc{self.__study.id}-sce{study_execution_identifier}-execution.log",
                )

        return file_path

    def setup_usecase(self, study_folder_path=None) -> [dict]:
        """
        Method to overload in order to provide data to the loaded study process
        Return a list of dictionary [{str: *}]

        :param study_folder_path: location of pickle file to load (optional parameter)
        :type study_folder_path: str
        """
        study_folder = study_folder_path
        if study_folder_path is None:
            study_folder = self.__root_dir

        return super().setup_usecase(study_folder)

    def setup_disciplines_data(self, study_folder_path=None) -> dict:
        """
        Method to overload in order to provide data to the loaded study process
        from a specific way
        Return a dictionary {str: *}

        :param study_folder_path: location of pickle file to load (optional parameter)
        :type study_folder_path: str

        :return dictionary, {str: *}
        """
        study_folder = study_folder_path
        if study_folder_path is None:
            study_folder = self.__root_dir

        return super().setup_disciplines_data(study_folder)

    def setup_cache_map_dict(self, study_folder_path=None) -> dict:
        """
        Method to overload in order to provide data to the loaded study process
        from a specific way
        Return a dictionary {str: *}

        :param study_folder_path: location of pickle file to load (optional parameter)
        :type study_folder_path: str
        """
        study_folder = study_folder_path
        if study_folder_path is None:
            study_folder = self.__root_dir

        return super().setup_cache_map_dict(study_folder)

    def set_error(self, error_message, disabled_study=False):
        """
        Set an error message on study case manager and flag True the error flag

        :param error_message: error message to set to this study case manager
        :type error_message: str

        :param disabled_study: disable study from the platform point of view (not seen by user and deleted on the next
        platform update
        :type disabled_study: boolean
        """
        self.load_status = LoadStatus.IN_ERROR
        self.__error_message = error_message

        with app.app_context():
            study_case = StudyCase.query.filter(
                StudyCase.id == self.__study_identifier,
            ).first()
            study_case.error = error_message
            study_case.disabled = disabled_study
            db.session.commit()

        self.__load_study_case_from_identifier()

    def clear_error(self):
        """
        Clear error on study case manager
        """
        self.load_status = LoadStatus.NONE
        self.__error_message = ""

    def update_study_case(self):
        """
        Force update of the study object from database
        """
        self.__load_study_case_from_identifier()

    def reset(self):
        """
        reset the exec_engine and force reload
        """
        self._build_execution_engine()
        self.clear_error()
        self.load_status = LoadStatus.NONE

    
    def load_study_case_from_source(self, source_directory=None):

        if source_directory is None:
            source_directory = self.dump_directory

        self.load_data(source_directory, display_treeview=False)
        self.load_disciplines_data(source_directory)
        self.read_cache_pickle(source_directory)

    def save_study_case(self):
        # Persist data using the current persistence strategy
        self.dump_study(self.dump_directory)

    def save_study_read_only_mode_in_file(self):
        """
        save loaded study case into a json file to be retrieved before loading is completed, and save the dashboard
        """

        with app.app_context():
            # check study status is DONE

            #-------------------
            # save loaded study in read only mode
            loaded_study_case = LoadedStudyCase(self, False, True, None, True)
            # Apply ontology
            process_metadata = load_processes_metadata(
                [f"{loaded_study_case.study_case.repository}.{loaded_study_case.study_case.process}"])

            repository_metadata = load_repositories_metadata(
                [loaded_study_case.study_case.repository])

            loaded_study_case.study_case.apply_ontology(
                process_metadata, repository_metadata)
            
            if self.execution_engine.root_process.status == ProxyDiscipline.STATUS_DONE:
                loaded_study_case.load_treeview_and_post_proc(
                        self, False, True, None, True)
                loaded_study_case.load_n2_diagrams(self)
                
                # fill loaded study data needed in read only file
                loaded_study_case.load_status = LoadStatus.READ_ONLY_MODE
                loaded_study_case.study_case.creation_status = StudyCase.CREATION_DONE
                loaded_study_case.study_case.has_read_only_file = True
                
                # retrieve execution data
                study_case_execution = StudyCaseExecution.query.filter(
                    StudyCaseExecution.id == loaded_study_case.study_case.current_execution_id).first()
                if study_case_execution is not None:
                    loaded_study_case.study_case.execution_status = study_case_execution.execution_status
                    loaded_study_case.study_case.last_memory_usage = study_case_execution.memory_usage
                    loaded_study_case.study_case.last_cpu_usage = study_case_execution.cpu_usage
                
                #----------------------------
                #save ontology data
                # retrieve ontology variable names and documentation ids  
                ontology_data = get_treenode_ontology_data(loaded_study_case.treenode)
                self.__get_and_save_ontology_usages({
                                                'disciplines': list(ontology_data.disciplines),
                                                'parameter_usages': list(ontology_data.parameter_usages)
                                            })
                self.__get_and_save_documentations(list(ontology_data.disciplines))

                #-------------------------
                #write read only mode file
                self.__read_only_rw_strategy.write_study_case_in_read_only_file(loaded_study_case, False)
                

                # save the study with no data for restricted read only access:
                loaded_study_case.load_treeview_and_post_proc(
                    self, True, True, None, True)
                self.__read_only_rw_strategy.write_study_case_in_read_only_file(loaded_study_case, True)

                #-------------------
                # save dashboard
                dashboard = generate_dashboard(
                    self.execution_engine, loaded_study_case.post_processings)
                self.__read_only_rw_strategy.write_dashboard(dashboard)

                #------------------
                # save execution logs in read only folder
                self.__read_only_rw_strategy.copy_file_in_read_only_folder(self.raw_log_file_path_absolute())

    
    def __get_and_save_ontology_usages(self, ontology_data:dict):
        """
        Get ontology usage from ontology server and save result.
        :param ontology_data: Request object is intended with the following data structure
        {
            ontology_request: {
                disciplines: string[], // list of disciplines string identifier
                parameter_usages: string[] // list of parameters string identifier
            }
        }
        ontology usages are saved in a json file next to the read only study file. 
        """
        try:
            # fetch ontology parameters usages
            all_ontology = load_ontology_usages(ontology_data)
        except Exception as ex:
            raise Exception(f"Error while retrieve ontology data: {str(ex)}")

        # save in ontology file
        try:
            # save in ontology.json file
            self.__read_only_rw_strategy.write_ontology(all_ontology)
        except Exception as ex:
            raise Exception(f"Error while writing ontology data: {str(ex)}")
        
        return True
    
    def __get_and_save_documentations(self, documentations_list):
        """
        Get documentation from ontology server and write result in files.
        :param documentations_list: list of disciplines ids to get there documentation
        The documentation is saved in markdown files in a folder "documentation" next to the study read only file

        """
        try:
            #fetch ontology documentation
            all_documentation = {}
            for doc in documentations_list:
                all_documentation[doc] = load_markdown_documentation_metadata(doc)
            
        except Exception as ex:
            raise Exception(f"Error while retrieve documentation data: {str(ex)}")

        # save in ontology file
        try:
            #save documentations in folder
            self.__read_only_rw_strategy.write_documentations(all_documentation)
        except Exception as ex:
            raise Exception(f"Error while writing documentation data: {str(ex)}")
        
        return True

    def get_local_ontology(self):
        """
        get content of the ontology saved file if exists, return None if not
        """
        return self.__read_only_rw_strategy.read_ontology()
    
    def get_local_documentation(self, documentation_name):
        """
        get content of the documentation md saved file if exists, return None if not
        """
        return self.__read_only_rw_strategy.read_documentation(documentation_name)

    def __load_study_case_from_identifier(self):
        """
        Methods that load a study case using the given study identifier
        from database
        """
        with app.app_context():
            study_cases = StudyCase.query.filter_by(id=self.__study_identifier)

            if study_cases is not None and study_cases.count() > 0:
                study_case = study_cases.first()

                self.__study = StudyCaseManager.UnboundStudyCase()
                self.__study.init_from_study_case(study_case)

            else:
                raise InvalidStudy(
                    f"Requested study case (identifier {self.__study_identifier}) does not exist in the database",
                )

    def __get_read_write_strategy(self):
        """
        Methods that determine and instantiate physical strategy serialisation
        """
        self.rw_strategy = DirectLoadDump()

        # Retrieve group owner
        owner_right = AccessRights.query.filter(
            AccessRights.access_right == AccessRights.OWNER,
        ).first()

        if owner_right is not None:
            study_group = (
                Group.query.join(StudyCaseAccessGroup)
                .filter(StudyCaseAccessGroup.study_case_id == self.__study_identifier)
                .filter(StudyCaseAccessGroup.right_id == owner_right.id)
                .first()
            )

            if study_group is not None:
                if study_group.confidential:
                    config = Config()
                    self.rw_strategy = CryptedLoadDump(
                        private_key_file=config.rsa_private_key_file,
                        public_key_file=config.rsa_public_key_file,
                    )

    def attach_logger(self, bulk_transaction=False):
        """
        Add database logger dedicated to study case using execution engine

        :param bulk_transaction,  boolean that enable or not record management by bulk regarding the database
            Activate bulk transaction improve performance regarding calculation but it is necessary
            to flush data calling flush method at the end of the process
        :type bulk_transaction: boolean
        """
        if self.__study_database_logger is None and self.logger is not None:

            config = Config()

            self.__study_database_logger = StudyCaseSQLAlchemyHandler(
                study_case_id=self.__study_identifier,
                bulk_transaction=bulk_transaction,
            )

            self.logger.addHandler(self.__study_database_logger)

    def detach_logger(self):
        """
        Detach database logger
        """
        if self.__study_database_logger is not None and self.logger is not None:
            self.logger.removeHandler(self.__study_database_logger)

        self.__study_database_logger = None

    def check_study_can_reload(self) -> bool:
        """
        Check that backup files exists
        """
        root_folder = Path(self.dump_directory)

        # check that there is backup files
        backup_files = list(
            root_folder.rglob(f"*{StudyCaseManager.BACKUP_FILE_NAME}.*"),
        )
        return len(backup_files) > 0

    def study_case_manager_save_backup_files(self):
        """
        Method that copy the study pickles into backup files
        """
        backup_done = False
        root_folder = Path(self.dump_directory)

        # check that there is no backup file already
        backup_files = list(root_folder.rglob(f"*{self.BACKUP_FILE_NAME}.*"))
        if len(backup_files) == 0:
            # get all files in directory
            files = list(root_folder.glob("*.*"))

            for file in files:
                # create backup file name
                file_and_extension = file.name.split(".")
                backup_file_name = (
                    file_and_extension[0]
                    + self.BACKUP_FILE_NAME
                    + "."
                    + file_and_extension[1]
                )

                # copy file into backup file:
                copy(root_folder.joinpath(file),
                     root_folder.joinpath(backup_file_name))
            backup_done = True
        return backup_done

    def study_case_manager_reload_backup_files(self):
        """
        Method that copy the study pickles backup files in place of the study pickles
        """
        reload_done = False
        root_folder = Path(self.dump_directory)

        app.logger.warning(f"Reloading study case {self.__study_identifier}")

        # check that there is backup files
        backup_files = list(root_folder.rglob(f"*{self.BACKUP_FILE_NAME}.*"))
        if len(backup_files) > 0:
            for backup_file in backup_files:
                # create backup file name
                backup_file_and_extension = backup_file.name.split(".")
                file_name = backup_file.name.replace(self.BACKUP_FILE_NAME, "")

                # copy backup file in place of pickle:
                copy(root_folder.joinpath(backup_file),
                     root_folder.joinpath(file_name))
            reload_done = True

        return reload_done

    
    def get_read_only_file_path(self, no_data=False):
        """
        Return the read only mode file path
        :param no_data: if true, return the path to the restricted viewer file instead of the read only file
        :type no_data: bool
        """
        return self.__read_only_rw_strategy.get_read_only_file_path(no_data)


    def read_loaded_study_case_in_json_file(self, no_data=False):
        """
        Retrieve study case loaded from json file for read only mode
        """
        return self.__read_only_rw_strategy.read_study_case_in_read_only_file(no_data)

    def delete_loaded_study_case_in_json_file(self):
        """
        Delete the read only foler containing all read only files
        """
        self.__read_only_rw_strategy.delete_read_only_mode()


    def check_study_case_json_file_exists(self):
        """
        Check study case loaded into json file for read only mode exists
        """
        return self.__read_only_rw_strategy.read_only_exists
    

    def read_dashboard_in_json_file(self):
        """
        Retrieve dashboard from json file
        """
        return self.__read_only_rw_strategy.read_dashboard()

    def get_parameter_data(self, parameter_key):
        """
        returns BytesIO of the data, read into the pickle
        """
        # get the anonimized key to retrieve the data into the pickle
        anonymize_key = self.execution_engine.anonymize_key(parameter_key)

        # read pickle
        input_datas = self._get_data_from_file(self.dump_directory)
        if len(input_datas) > 0:
            if anonymize_key in input_datas[0].keys():
                data_value = input_datas[0][anonymize_key]
                # convert data into dataframe then ioBytes to have the same
                # format as if retrieved from the dm
                if data_value is None:
                    return None
                else:
                    serializer = DataSerializer()
                    df_data = serializer.convert_to_dataframe_and_bytes_io(
                        data_value, parameter_key)
                    return df_data

        # it should never be there because an exception should be raised if the
        # file could not be red
        return None
    

    def get_n2_diagram_graph_data(self)-> dict:
        """
        Get coupling chart for visualisation part
        """

        # Get couplings
        couplings = self.execution_engine.root_process.export_couplings()
        if couplings is None:
            raise Exception("Failed to export couplings")

        # Get treeview data
        treeview = self.execution_engine.get_treeview()
        if treeview is None:
            raise Exception("Failed to get treeview")

        # Load matrix and generate graph from ontology
        ontology_matrix_data = load_n2_matrix(treeview)
        graph = {}
        if len(ontology_matrix_data) > 0:

            # Get couplings graph from matrix
            graph = get_couplings_force_graph(couplings, ontology_matrix_data)

        return graph
    

    def get_execution_sequence_graph_data(self)-> dict:
        """
        Generate execution sequence for visualisation part
        """
        GEMS_graph = self.execution_engine.root_process.coupling_structure.graph

        # execution workflow generation
        execution_workflow = SoSExecutionWorkflow(GEMS_graph)
        execution_workflow.get_execution_workflow_graph()

        result = execution_workflow.create_result()

        return result
    
    def get_interface_diagram_graph_data(self)-> dict:
        """
        Generate execution sequence for visualisation part
        """
        interface_diagram = InterfaceDiagramGenerator(self)
        result = interface_diagram.generate_interface_diagram_data()

        return result
    
    def export_study_read_only_zip(self, zip_file_path)->bool:

        # create a zip archive containing the read_only_mode folder
        # plus the pkl files
        if not self.__read_only_rw_strategy.read_only_exists:
            return False
            
        elements_to_zip = []

        dm_pkl_file = join(self.dump_directory, DataSerializer.pkl_filename)
        status_pkl_file = join(self.dump_directory, DataSerializer.disc_status_filename)
        
        # add pkl file to zip
        if os.path.exists(dm_pkl_file):
            elements_to_zip.append(dm_pkl_file)
        # add status file to zip
        if os.path.exists(status_pkl_file):
            elements_to_zip.append(status_pkl_file)

         # Add study metadata in the zip file
        metadata = self.__study.serialize_standalone()

        # add read only files into the folder
        elements_to_zip.append(self.__read_only_rw_strategy.read_only_folder_path)

        zip_files_and_folders(zip_file_path, elements_to_zip, json.dumps(metadata))

        return True
    
    def check_study_standalone_files(self)->bool:
        dm_pkl_file = join(self.dump_directory, DataSerializer.pkl_filename)
        status_pkl_file = join(self.dump_directory, DataSerializer.disc_status_filename)
 
        # add pkl file to zip
        return os.path.exists(dm_pkl_file) and os.path.exists(status_pkl_file) and self.__read_only_rw_strategy.read_only_exists


    @staticmethod
    def copy_pkl_file(file_name, study_case_manager, study_manager_source):
        """
        Load data from a file then dump them into a new file
        """
        # Create the new study's directory
        if not os.path.exists(study_case_manager.dump_directory):
            os.makedirs(study_case_manager.dump_directory)

        initial_file_path = os.path.join(study_manager_source.dump_directory, file_name)
        file_path_final = os.path.join(study_case_manager.dump_directory, file_name)

        if file_path_final and initial_file_path is not None:
            data_dict = study_manager_source.rw_strategy.load(initial_file_path)
            study_case_manager.rw_strategy.dump(data_dict, file_path_final)

    @staticmethod
    def get_root_study_data_folder(group_id=None, study_case_id=None) -> str:
        """
        Return path of the study case or group data

        :param group_id: optional id of the group
        :type group_id: int

        :param study_case_id: optional id of the study_case
        :type study_case_id: int
        """
        data_root_dir = join(Config().data_root_dir, "study_case")
        if group_id is not None:
            data_root_dir = join(data_root_dir, str(group_id))
            if study_case_id is not None:
                data_root_dir = join(data_root_dir, str(study_case_id))

        return data_root_dir
