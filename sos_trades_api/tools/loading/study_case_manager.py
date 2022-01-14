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
Implementation of abstract class AbstractStudyManager to manage study from object use into the WEBAPI
"""

from sos_trades_core.study_manager.base_study_manager import BaseStudyManager
from sos_trades_api.models.database_models import StudyCase, StudyCaseAccessGroup, \
    Group, AccessRights
from sos_trades_api.base_server import db, app
from sos_trades_core.tools.rw.load_dump_dm_data import DirectLoadDump,\
    CryptedLoadDump
from sos_trades_api.config import Config
from os.path import join

import os

from eventlet import sleep
from sos_trades_api.tools.logger.execution_mysql_handler import ExecutionMySQLHandler
from sos_trades_core.api import get_sos_logger
from pathlib import Path
from shutil import copy


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

    def __init__(self, study_identifier, logger_bulk_transaction=False):
        """ Constructor 

        :param study_identifier, database study identifier
        :type str

        :param logger_bulk_transaction,  boolean that enable or not record management by bulk regarding the database
                Activate bulk transaction improve performance regarding calculation but it is necessary 
                to flush data calling flush method at the end of the process
        :type boolean
        """
        self.__study_identifier = study_identifier
        self.__study = None

        self.__load_study_case_from_identifier()

        self.__rw_strategy = None
        self.__get_read_write_strategy()

        self.__root_dir = self.get_root_study_data_folder(self.__study.group_id, self.__study.id)

        super().__init__(self.__study.repository,
                         self.__study.process, self.__study.name, self.__root_dir, yield_method=sleep, logger=get_sos_logger(f'{self.__study_identifier}.SoS.EE'))

        self.__study_database_logger = None
        self.__create_logger(logger_bulk_transaction)

        self.load_in_progress = False
        self.loaded = False
        self.n2_diagram = {}

        self.__has_error = False
        self.__error_message = ""


    @property
    def study(self):
        """ return the current Study object

        :return sos_trades_api.models.database_models.StudyCase
        """
        return self.__study

    @property
    def study_database_logger(self):
        """ return the current database logger handler used by the study

        :return sos_trades_api.tools.logger.execution_mysql_handler.ExecutionMySQLHandler
        """

        return self.__study_database_logger

    @property
    def has_error(self):
        """ return the current error flag

        :return boolean
        """

        return self.__has_error

    @property
    def error_message(self):
        """ return the current error message

        :return string
        """

        return self.__error_message

    @property
    def add_execution_identifier(self):
        """ return property value (add execution identifier into database log)

        :return: boolean
        """
        return self.__study_database_logger.study_case_execution_identifier is None

    @add_execution_identifier.setter
    def add_execution_identifier(self, value):
        """

        :param value: add or not execution identifier to database log
        :type boolean
        """

        if value is True:
            self.__study_database_logger.study_case_execution_identifier = self.__study.current_execution_id
        else:
            self.__study_database_logger.study_case_execution_identifier = None

    def raw_log_file_path_absolute(self, specific_study_case_execution_identifier=None):
        """
        Build the raw log file path of the study

        :param specific_study_case_execution_identifier: Optional, to retireve execution which is not the current one in
        the study case
        :return: str (filepath)
        """

        file_path = ''

        if self.__study is not None:

            study_execution_identifier = self.__study.current_execution_id
            if specific_study_case_execution_identifier is not None:
                study_execution_identifier = specific_study_case_execution_identifier

            file_path = os.path.join(self.dump_directory,
                                     f'sc{self.__study.id}-sce{study_execution_identifier}-execution.log')

        return file_path

    def raw_log_file_path_relative(self, specific_study_case_execution_identifier=None):
        """
        Build the raw log file path of the study

        :param specific_study_case_execution_identifier: Optional, to retireve execution which is not the current one in
        the study case
        :return: str
        """

        file_path = ''

        if self.__study is not None:

            study_execution_identifier = self.__study.current_execution_id
            if specific_study_case_execution_identifier is not None:
                study_execution_identifier = specific_study_case_execution_identifier

            file_path = os.path.join(str(self.__study.group_id),
                                     str(self.__study.id),
                                     f'sc{self.__study.id}-sce{study_execution_identifier}-execution.log')

        return file_path

    def setup_usecase(self, study_folder_path=None):
        """ Method to overload in order to provide data to the loaded study process

        :param study_folder_path, location of pickle file to load (optional parameter)
        :type str

        :return list od dictionary, [{str: *}]
        """

        study_folder = study_folder_path
        if study_folder_path is None:
            study_folder = self.__root_dir

        return self._get_data_from_file(study_folder)

    def setup_disciplines_data(self, study_folder_path=None):
        """ Method to overload in order to provide data to the loaded study process
        from a specific way

        :param study_folder_path, location of pickle file to load (optional parameter)
        :type str

        :return dictionary, {str: *}
        """

        study_folder = study_folder_path
        if study_folder_path is None:
            study_folder = self.__root_dir

        return self._get_disciplines_data_from_file(study_folder)

    def set_error(self, error_message, disabled_study=False):
        """ set an error message on study case manager and flag True the error flag
        """

        self.__has_error = True
        self.__error_message = error_message

        with app.app_context():
            study_case = StudyCase.query.filter(
                StudyCase.id == self.__study_identifier).first()
            study_case.error = error_message
            study_case.disabled = disabled_study
            db.session.commit()

        self.__load_study_case_from_identifier()

    def clear_error(self):
        """ Clear error on study case manager
        """

        self.__has_error = False
        self.__error_message = ""

    def update_study_case(self):
        """ Force update of the study object from database
        """

        self.__load_study_case_from_identifier()

    def reset(self):
        """ reset the exec_engine and force reload
        """
        """ Create an instance of the execution engine
        """
        self._init_exec_engine()
        self.clear_error()
        self.load_in_progress = False
        self.loaded = False

    def __load_study_case_from_identifier(self):
        """ Methods that load a study case using the given study identifier
        from database
        """

        with app.app_context():
            studycases = StudyCase.query.filter_by(id=self.__study_identifier)

            if studycases is not None and studycases.count() > 0:
                studycase = studycases.first()
                db.session.expunge(studycase)
                self.__study = studycase
            else:
                raise InvalidStudy(
                    f'Requested study case (identifier {self.__study_identifier}) does not exist in the database')

    def __get_read_write_strategy(self):
        """ Methods that determine and instanciate plysical strategy serialisation
        """

        self.rw_strategy = DirectLoadDump()

        # Retrieve group owner
        owner_right = AccessRights.query.filter(
            AccessRights.access_right == AccessRights.OWNER).first()

        if owner_right is not None:
            study_group = Group.query.join(StudyCaseAccessGroup)\
                .filter(StudyCaseAccessGroup.study_case_id == self.__study_identifier)\
                .filter(StudyCaseAccessGroup.right_id == owner_right.id).first()

            if study_group is not None:
                if study_group.confidential:
                    config = Config()
                    self.rw_strategy = CryptedLoadDump(private_key_file=config.rsa_private_key_file,
                                                       public_key_file=config.rsa_public_key_file)

    def __create_logger(self, bulk_transaction):
        """ Add database logger dedicated to study case using execution engine

            :param logger_bulk_transaction,  boolean that enable or not record management by bulk regarding the database
                Activate bulk transaction improve performance regarding calculation but it is necessary 
                to flush data calling flush method at the end of the process
            :type boolean
        """

        if self.__study_database_logger is None and self.logger is not None:

            config = Config()

            ssl_configuration = {}

            if config.sql_alchemy_database_ssl is not None:
                ssl_configuration = {"ssl": config.sql_alchemy_database_ssl}

            self.__study_database_logger = ExecutionMySQLHandler(
                config.sql_alchemy_database_name, config.sql_alchemy_server_uri,
                ssl_configuration, self.__study_identifier, bulk_transaction)

            # disable execution handler
            # self.logger.addHandler(self.__study_database_logger)

    def check_study_can_reload(self):
        """
        Check that backup files exists
        """
        root_folder = Path(self.dump_directory)

        # check that there is backup files
        backup_files = list(root_folder.rglob(f'*{StudyCaseManager.BACKUP_FILE_NAME}.*'))
        return len(backup_files) > 0

    def study_case_manager_save_backup_files(self):
        """ Method that copy the study pickles into backup files
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
                backup_file_name = file_and_extension[0] + self.BACKUP_FILE_NAME + "." + file_and_extension[1]

                # copy file into backup file:
                copy(root_folder.joinpath(file), root_folder.joinpath(backup_file_name))
            backup_done = True
        return backup_done

    def study_case_manager_reload_backup_files(self):
        """ Method that copy the study pickles backup files in place of the study pickles
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

    @staticmethod
    def get_root_study_data_folder(group_id=None, study_case_id=None):
        """
        return path of the study case or group data
        :param:group_id, optional id of the group
        :type: int
        :param:study_case_id, optional id of the study_case
        :type: int
        """
        data_root_dir = join(Config().data_root_dir, 'study_case')
        if group_id is not None:
            data_root_dir = join(data_root_dir, str(group_id))
            if study_case_id is not None:
                data_root_dir = join(data_root_dir, str(study_case_id))

        return data_root_dir

