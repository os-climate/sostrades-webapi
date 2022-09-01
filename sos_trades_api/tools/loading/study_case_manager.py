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
import time

from sos_trades_api.tools.file_tools import read_object_in_json_file, write_object_in_json_file
from sos_trades_core.execution_engine.sos_discipline import SoSDiscipline

"""
mode: python; py-indent-offset: 4; tab-width: 4; coding: utf-8
Implementation of abstract class AbstractStudyManager to manage study from object use into the WEBAPI
"""

from sos_trades_core.study_manager.base_study_manager import BaseStudyManager
from sos_trades_core.tools.tree.serializer import DataSerializer
from sos_trades_core.tools.dashboard.dashboard_factory import generate_dashboard
from sos_trades_api.models.database_models import (
    StudyCase,
    StudyCaseAccessGroup,
    Group,
    AccessRights,
)
from sos_trades_core.execution_engine.data_connector.ontology_data_connector import (
    GLOBAL_EXECUTION_ENGINE_ONTOLOGY_IDENTIFIER,
    OntologyDataConnector,
)
from sos_trades_api.base_server import db, app
from sos_trades_core.tools.rw.load_dump_dm_data import DirectLoadDump, CryptedLoadDump
from sos_trades_api.config import Config
from os.path import join


import os

from eventlet import sleep
from sos_trades_api.tools.logger.study_case_mysql_handler import StudyCaseMySQLHandler
from sos_trades_core.api import get_sos_logger
from pathlib import Path
from shutil import copy
import json
from sos_trades_api.models.custom_json_encoder import CustomJsonEncoder
from sos_trades_api.models.loaded_study_case import LoadedStudyCase, LoadStatus


class StudyCaseError(Exception):
    """Base StudyCase Exception"""

    def __init__(self, msg=None):
        Exception.__init__(self, msg)

    def __str__(self):
        return self.__class__.__name__ + '(' + Exception.__str__(self) + ')'


class InvalidProcess(StudyCaseError):
    """Invalid process (Raise an error while trying to load it)"""


class InvalidStudy(StudyCaseError):
    """Invalid study"""


class StudyCaseManager(BaseStudyManager):
    BACKUP_FILE_NAME = "_backup"
    LOADED_STUDY_FILE_NAME = "loaded_study_case.json"
    DASHBOARD_FILE_NAME = "dashboard.json"

    def __init__(self, study_identifier):
        """
        Constructor

        :param study_identifier: database study identifier
        :type study_identifier: str

        """
        self.__study_identifier = study_identifier
        self.__study = None

        self.__load_study_case_from_identifier()

        self.__rw_strategy = None
        self.__get_read_write_strategy()

        self.__root_dir = self.get_root_study_data_folder(
            self.__study.group_id, self.__study.id
        )

        super().__init__(
            self.__study.repository,
            self.__study.process,
            self.__study.name,
            self.__root_dir,
            yield_method=sleep,
            logger=get_sos_logger(f'{self.__study_identifier}.SoS.EE'),
        )

        self.__study_database_logger = None

        self.load_status = LoadStatus.NONE
        self.n2_diagram = {}
        self.__error_message = ""

    @property
    def study(self) -> StudyCase:
        """
        Return the current Study object
        """
        return self.__study

    @property
    def study_database_logger(self) -> StudyCaseMySQLHandler:
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
        self.execution_engine.connector_container.register_persistent_connector(
            OntologyDataConnector.NAME,
            GLOBAL_EXECUTION_ENGINE_ONTOLOGY_IDENTIFIER,
            {'endpoint': app.config["SOS_TRADES_ONTOLOGY_ENDPOINT"]},
        )

    def raw_log_file_path_absolute(
        self, specific_study_case_execution_identifier=None
    ) -> str:
        """
        Build the raw log file path of the study

        :param specific_study_case_execution_identifier: Optional, to retrieve execution which is not the current one in
        the study case
        :type specific_study_case_execution_identifier: str/int
        """

        file_path = ''

        if self.__study is not None:

            study_execution_identifier = self.__study.current_execution_id
            if specific_study_case_execution_identifier is not None:
                study_execution_identifier = specific_study_case_execution_identifier

            file_path = os.path.join(
                self.dump_directory,
                f'sc{self.__study.id}-sce{study_execution_identifier}-execution.log',
            )

        return file_path

    def raw_log_file_path_relative(
        self, specific_study_case_execution_identifier=None
    ) -> str:
        """
        Build the raw log file path of the study

        :param specific_study_case_execution_identifier: Optional, to retrieve execution which is not the current one in
        the study case
        """

        file_path = ''

        if self.__study is not None:

            study_execution_identifier = self.__study.current_execution_id
            if specific_study_case_execution_identifier is not None:
                study_execution_identifier = specific_study_case_execution_identifier

            file_path = os.path.join(
                str(self.__study.group_id),
                str(self.__study.id),
                f'sc{self.__study.id}-sce{study_execution_identifier}-execution.log',
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
                StudyCase.id == self.__study_identifier
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

    def load_study_case_from_source(self, source_directory):
        self.load_data(source_directory, display_treeview=False)
        self.load_disciplines_data(source_directory)
        self.load_cache(source_directory)

    def save_study_case(self):
        # Persist data using the current persistence strategy
        self.dump_data(self.dump_directory)
        self.dump_disciplines_data(self.dump_directory)
        self.dump_cache(self.dump_directory)

    def save_study_read_only_mode_in_file(self):
        """
        save loaded study case into a json file to be retrieved before loading is completed, and save the dashboard
        """
        with app.app_context():
            #-------------------
            # save loaded study in read only mode
            loaded_study_case = LoadedStudyCase(self, False, True, None, True)
            # if the loaded status is not yet at LOADED, load treeview post proc anyway
            if self.load_status != LoadStatus.LOADED:
                loaded_study_case.load_treeview_and_post_proc(self,False,True,None, True)
            loaded_study_case.load_status = LoadStatus.READ_ONLY_MODE
            self.__write_loaded_study_case_in_json_file(loaded_study_case)

            #-------------------
            # save dashboard if the process is DONE
            if self.execution_engine.root_process.status == SoSDiscipline.STATUS_DONE:
                dashboard = generate_dashboard(self.execution_engine, loaded_study_case.post_processings)
                dashboard_file_path = Path(self.dump_directory).joinpath(self.DASHBOARD_FILE_NAME)
                write_object_in_json_file(dashboard, dashboard_file_path)


    def __load_study_case_from_identifier(self):
        """
        Methods that load a study case using the given study identifier
        from database
        """

        with app.app_context():
            study_cases = StudyCase.query.filter_by(id=self.__study_identifier)

            if study_cases is not None and study_cases.count() > 0:
                study_case = study_cases.first()
                db.session.expunge(study_case)
                self.__study = study_case
            else:
                raise InvalidStudy(
                    f'Requested study case (identifier {self.__study_identifier}) does not exist in the database'
                )

    def __get_read_write_strategy(self):
        """
        Methods that determine and instantiate physical strategy serialisation
        """

        self.rw_strategy = DirectLoadDump()

        # Retrieve group owner
        owner_right = AccessRights.query.filter(
            AccessRights.access_right == AccessRights.OWNER
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

            ssl_configuration = {}

            if config.sql_alchemy_database_ssl is not None:
                ssl_configuration = {"ssl": config.sql_alchemy_database_ssl}

            self.__study_database_logger = StudyCaseMySQLHandler(
                config.sql_alchemy_database_name,
                config.sql_alchemy_server_uri,
                ssl_configuration,
                self.__study_identifier,
                bulk_transaction,
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
            root_folder.rglob(f'*{StudyCaseManager.BACKUP_FILE_NAME}.*')
        )
        return len(backup_files) > 0

    def study_case_manager_save_backup_files(self):
        """
        Method that copy the study pickles into backup files
        """

        backup_done = False
        root_folder = Path(self.dump_directory)

        # check that there is no backup file already
        backup_files = list(root_folder.rglob(f'*{self.BACKUP_FILE_NAME}.*'))
        if len(backup_files) == 0:
            # get all files in directory
            files = list(root_folder.glob(f'*.*'))

            for file in files:
                # create backup file name
                file_and_extension = file.name.split('.')
                backup_file_name = (
                    file_and_extension[0]
                    + self.BACKUP_FILE_NAME
                    + "."
                    + file_and_extension[1]
                )

                # copy file into backup file:
                copy(root_folder.joinpath(file), root_folder.joinpath(backup_file_name))
            backup_done = True
        return backup_done

    def study_case_manager_reload_backup_files(self):
        """
        Method that copy the study pickles backup files in place of the study pickles
        """

        reload_done = False
        root_folder = Path(self.dump_directory)

        # check that there is backup files
        backup_files = list(root_folder.rglob(f'*{self.BACKUP_FILE_NAME}.*'))
        if len(backup_files) > 0:
            for backup_file in backup_files:
                # create backup file name
                backup_file_and_extension = backup_file.name.split('.')
                file_name = backup_file.name.replace(self.BACKUP_FILE_NAME, '')

                # copy backup file in place of pickle:
                copy(root_folder.joinpath(backup_file), root_folder.joinpath(file_name))
            reload_done = True

        return reload_done

    def __write_loaded_study_case_in_json_file(self, loaded_study):
        """
        Save study case loaded into json file for read only mode
        :param loaded_study: loaded_study_case to save
        :type loaded_study: LoadedStudyCase
        """
        study_file_path = Path(self.dump_directory).joinpath(self.LOADED_STUDY_FILE_NAME)
        return write_object_in_json_file(loaded_study, study_file_path)


    def read_loaded_study_case_in_json_file(self):
        """
        Retrieve study case loaded from json file for read only mode
        """
        root_folder = Path(self.dump_directory)
        study_file_path = root_folder.joinpath(self.LOADED_STUDY_FILE_NAME)
        loaded_study = read_object_in_json_file(study_file_path)

        return loaded_study

    def delete_loaded_study_case_in_json_file(self):
        """
        Retrieve study case loaded from json file for read only mode
        """
        root_folder = Path(self.dump_directory)
        study_file_path = root_folder.joinpath(self.LOADED_STUDY_FILE_NAME)
        if os.path.exists(study_file_path):
            os.remove(study_file_path)

    def check_study_case_json_file_exists(self):
        """
        Check study case loaded into json file for read only mode exists
        """
        root_folder = Path(self.dump_directory)
        file_path = root_folder.joinpath(self.LOADED_STUDY_FILE_NAME)

        return os.path.exists(file_path)

    def read_dashboard_in_json_file(self):
        """
        Retrieve dashboard from json file
        """
        root_folder = Path(self.dump_directory)
        file_path = root_folder.joinpath(self.DASHBOARD_FILE_NAME)
        return read_object_in_json_file(file_path)

    def delete_dashboard_json_file(self):
        """
        delete dashboard json file
        """
        root_folder = Path(self.dump_directory)
        file_path = root_folder.joinpath(self.DASHBOARD_FILE_NAME)
        if os.path.exists(file_path):
            os.remove(file_path)

    def check_dashboard_json_file_exists(self):
        """
        Check dashboard json file exists
        """
        root_folder = Path(self.dump_directory)
        file_path = root_folder.joinpath(self.DASHBOARD_FILE_NAME)

        return os.path.exists(file_path)

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
                # convert data into dataframe then ioBytes to have the same format as if retrieved from the dm
                df_data = DataSerializer.convert_to_dataframe_and_bytes_io(data_value, parameter_key)
                return df_data

        # it should never be there because an exception should be raised if the file could not be red
        return None

    @staticmethod
    def get_root_study_data_folder(group_id=None, study_case_id=None) -> str:
        """
        Return path of the study case or group data

        :param group_id: optional id of the group
        :type group_id: int

        :param study_case_id: optional id of the study_case
        :type study_case_id: int
        """

        data_root_dir = join(Config().data_root_dir, 'study_case')
        if group_id is not None:
            data_root_dir = join(data_root_dir, str(group_id))
            if study_case_id is not None:
                data_root_dir = join(data_root_dir, str(study_case_id))

        return data_root_dir

