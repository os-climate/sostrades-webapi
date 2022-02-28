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
Flask and database configuration variable
"""
import os
from copy import deepcopy
from os.path import join, dirname, abspath
from pathlib import Path
from builtins import property
import yaml
import json

BASEDIR = abspath(dirname(__file__))

# pylint: disable=line-too-long
# pylint: disable=too-many-instance-attributes


class Config():

    """ Flask configuration class

    Flask and database configuration variable only used for development environment
    Production environment is overwritten using an external configuration
    file
    """

    #
    # FLASK CONFIGURATION SECTION END

    CONFIG_FILENAME = 'sos_trades_config.yaml'

    # Environment configuration variable names
    CONFIG_DATA_ROOT_DIR_ENV_VAR = "SOS_TRADES_DATA"
    CONFIG_REFERENCE_ROOT_DIR_ENV_VAR = "SOS_TRADES_REFERENCES"
    CONFIG_EXECUTION_STRATEGY_ENV_VAR = "SOS_TRADES_EXECUTION_STRATEGY"  # for values : 'subprocess', 'kubernetes'

    CONFIG_EXECUTION_STRATEGY_THREAD = 'thread'
    CONFIG_EXECUTION_STRATEGY_SUBPROCESS = 'subprocess'
    CONFIG_EXECUTION_STRATEGY_K8S = 'kubernetes'

    CONFIG_EEB_CONFIGURATION_FILE_ENV_VAR = "EEB_PATH"
    CONFIG_RSA_ROOT_DIR_ENV_VAR = "SOS_TRADES_RSA"

    def __init__(self):
        """Constructor
        """

#         self.repository_list = ['dev']
        self.icon_mapping = {}
        self.__server_config_file = {}

        self.__data_root_dir = ''
        self.__reference_root_dir = ''

        self.__available_strategies = [Config.CONFIG_EXECUTION_STRATEGY_THREAD,
                                       Config.CONFIG_EXECUTION_STRATEGY_SUBPROCESS,
                                       Config.CONFIG_EXECUTION_STRATEGY_K8S]
        self.__execution_strategy = ''

        self.__eeb_configuration_filepath = ''

        self.__rsa_root_dir = ''

        self.__rsa_public_key = ''
        self.__rsa_private_key = ''

        self.__logging_database_data = {}
        self.__logging_database_name = ''
        self.__main_database_data = {}
        self.__sql_alchemy_database_name = ''
        self.__sql_alchemy_database_ssl = None
        self.__sql_alchemy_server_uri = ''
        self.__sql_alchemy_full_uri = ''
        self.__secret_key = ''

        self.reference_root_dir_env_var = self.CONFIG_REFERENCE_ROOT_DIR_ENV_VAR
        self.execution_strategy_env_var = self.CONFIG_EXECUTION_STRATEGY_ENV_VAR
        self.eeb_path = self.CONFIG_EEB_CONFIGURATION_FILE_ENV_VAR
        self.rsa_root_dir_env_var = self.CONFIG_RSA_ROOT_DIR_ENV_VAR
        self.data_root_dir_env_var = self.CONFIG_DATA_ROOT_DIR_ENV_VAR

        filepath = join(BASEDIR, Config.CONFIG_FILENAME)
        if Path(filepath).is_file():
            with open(filepath) as file:
                config_data = yaml.safe_load(file)
                self.icon_mapping = config_data['icon-mapping']
        else:
            raise Exception(
                f'Application configuration file {Config.CONFIG_FILENAME} not found')

        if os.environ.get('SOS_TRADES_SERVER_CONFIGURATION') is not None:
            with open(os.environ['SOS_TRADES_SERVER_CONFIGURATION']) as server_conf_file:
                self.__server_config_file = json.load(server_conf_file)
        else:
            raise Exception(
                f'Environment variable "SOS_TRADES_SERVER_CONFIGURATION" not found')

    def check(self):
        """ Make a check on mandatory parameter to make sure configuration is correct
        Each property is able to raise an exception if it cannot found the necessary
        information to initialize
        """
        # pylint: disable=unused-variable

        # -------------------------------------------------------------------
        # This first section check all mandatory data needs to run the server
        data_root_dir = self.data_root_dir
        reference_root_dir = self.reference_root_dir
        rsa_public_key_file = self.rsa_public_key_file
        rsa_private_key_file = self.rsa_private_key_file

        # Execution strategy is mandatory. If kubernetes is chosen then check
        # if calculation manifest is available
        if self.execution_strategy is Config.CONFIG_EXECUTION_STRATEGY_K8S:
            eeb_filepath = self.eeb_filepath

        # pylint: enable=unused-variable

    @property
    def data_root_dir(self):
        """data root directory property get

        :return string (folder path)
        :raise ValueError exception
        """

        if len(self.__data_root_dir) == 0:
            if os.environ.get(self.data_root_dir_env_var) is None:
                raise ValueError(
                    f"Environment variable '{self.data_root_dir_env_var}' not provided")

            if not Path(os.environ[self.data_root_dir_env_var]).exists():
                try:
                    os.makedirs(
                        os.environ[self.data_root_dir_env_var], exist_ok=True)
                except Exception as error:
                    raise ValueError(
                        f"Environment variable '{self.data_root_dir_env_var}' values is not a valid folder path : {os.environ[self.data_root_dir_env_var]}\n{error}")
            else:
                self.__data_root_dir = os.environ[self.data_root_dir_env_var]

        return self.__data_root_dir

    @property
    def reference_root_dir(self):
        """reference data root directory property get

        :return string (folder path)
        :raise ValueError exception
        """

        if len(self.__reference_root_dir) == 0:
            if os.environ.get(self.reference_root_dir_env_var) is None:
                raise ValueError(
                    f"Environment variable '{self.reference_root_dir_env_var}' not provided")

            if not Path(os.environ[self.reference_root_dir_env_var]).exists():
                try:
                    os.makedirs(
                        os.environ[self.reference_root_dir_env_var], exist_ok=True)
                except Exception as error:
                    raise ValueError(
                        f"Environment variable '{self.reference_root_dir_env_var}' values is not a valid folder path : {os.environ[self.reference_root_dir_env_var]}\n{error}")
            else:
                self.__reference_root_dir = os.environ[self.reference_root_dir_env_var]

        return self.__reference_root_dir

    @property
    def execution_strategy(self):
        """execution strategy property get

        :return string ('thread', 'subprocess', 'kubernetes')
        :raise ValueError exception
        """

        if len(self.__execution_strategy) == 0:
            if os.environ.get(self.execution_strategy_env_var) is None:
                raise ValueError(
                    f"Environment variable '{self.execution_strategy_env_var}' not provided")

            if not len(os.environ[self.execution_strategy_env_var]) > 0:
                raise ValueError(
                    f"Environment variable '{self.execution_strategy_env_var}' has no value, any of the following is intended : {self.__available_strategies}")

            if os.environ[self.execution_strategy_env_var] not in self.__available_strategies:
                raise ValueError(
                    f"Environment variable '{self.execution_strategy_env_var}' value is unknown, any of the following is intended : {self.__available_strategies}")

            self.__execution_strategy = os.environ[self.execution_strategy_env_var]

        return self.__execution_strategy

    @property
    def eeb_filepath(self):
        """execution engine block kubernets configuration property get

        :return string (filepath)
        :raise ValueError exception
        """

        if len(self.__eeb_configuration_filepath) == 0:
            if os.environ.get(self.eeb_path) is None:
                raise ValueError(
                    f"Environment variable '{self.eeb_path}' not provided")

            if not Path(os.environ[self.eeb_path]).exists():
                raise ValueError(
                    f"Environment variable '{self.eeb_path}' values is not a valid filepath : {os.environ[self.eeb_path]}")

            self.__eeb_configuration_filepath = os.environ[self.eeb_path]

        return self.__eeb_configuration_filepath

    @property
    def rsa_public_key_file(self):
        """rsa public key property get

        :return string (filepath)
        :raise ValueError exception
        """

        if len(self.__rsa_public_key) == 0:
            if os.environ.get(self.rsa_root_dir_env_var) is None:
                raise ValueError(
                    f"Environment variable '{self.rsa_root_dir_env_var}' not provided")

            if not Path(os.environ[self.rsa_root_dir_env_var]).exists():
                raise ValueError(
                    f"Environment variable '{self.rsa_root_dir_env_var}' values is not a valid folder : {os.environ[self.rsa_root_dir_env_var]}")

            if not Path(join(os.environ[self.rsa_root_dir_env_var], 'public_key.pem')).exists():
                raise ValueError(
                    f"Public rsa key not found at the specified filepath: {join(os.environ[self.rsa_root_dir_env_var], 'public_key.pem')}")

            self.__rsa_public_key = join(
                os.environ[self.rsa_root_dir_env_var], 'public_key.pem')

        return self.__rsa_public_key

    @property
    def rsa_private_key_file(self):
        """rsa private key property get

        :return string (filepath)
        :raise ValueError exception
        """

        if len(self.__rsa_private_key) == 0:
            if os.environ.get(self.rsa_root_dir_env_var) is None:
                raise ValueError(
                    f"Environment variable '{self.rsa_root_dir_env_var}' not provided")

            if not Path(os.environ[self.rsa_root_dir_env_var]).exists():
                raise ValueError(
                    f"Environment variable '{self.rsa_root_dir_env_var}' values is not a valid folder : {os.environ[self.rsa_root_dir_env_var]}")

            if not Path(join(os.environ[self.rsa_root_dir_env_var], 'private_key.pem')).exists():
                raise ValueError(
                    f"Private rsa key not found at the specified filepath: {join(os.environ[self.rsa_root_dir_env_var], 'private_key.pem')}")

            self.__rsa_private_key = join(
                os.environ[self.rsa_root_dir_env_var], 'private_key.pem')

        return self.__rsa_private_key

    @property
    def sql_alchemy_database_name(self):
        """sql alchemy database name, key property get

        :return string (sql alchemy database name)
        :raise ValueError exception
        """
        if len(self.__sql_alchemy_database_name) == 0:
            self.__sql_alchemy_database_name = self.__server_config_file['SQL_ALCHEMY_DATABASE']['DATABASE_NAME']
        return self.__sql_alchemy_database_name

    @property
    def sql_alchemy_server_uri(self):
        """sql alchemy server uri, key property get

        :return string (sql alchemy server uri)
        :raise ValueError exception
        """
        if len(self.__sql_alchemy_server_uri) == 0:
            error_env_msgs = []

            sql_alchemy_user = os.environ.get(self.__server_config_file['SQL_ALCHEMY_DATABASE']['USER_ENV_VAR'])
            if sql_alchemy_user is None:
                error_env_msgs.append(f"Environment variable "
                                      f"'{self.__server_config_file['SQL_ALCHEMY_DATABASE']['USER_ENV_VAR']} not provided")

            sql_alchemy_password = os.environ.get(self.__server_config_file['SQL_ALCHEMY_DATABASE']['PASSWORD_ENV_VAR'])
            if sql_alchemy_password is None:
                error_env_msgs.append(f"Environment variable "
                                      f"'{self.__server_config_file['SQL_ALCHEMY_DATABASE']['PASSWORD_ENV_VAR']} not provided")

            if len(error_env_msgs) > 0:
                raise ValueError("\n".join(error_env_msgs))

            # Set SQL Alchemy database URI
            self.__sql_alchemy_server_uri = f'mysql+mysqldb://{sql_alchemy_user}:{sql_alchemy_password}@' \
                                               f'{self.__server_config_file["SQL_ALCHEMY_DATABASE"]["HOST"]}:' \
                                               f'{self.__server_config_file["SQL_ALCHEMY_DATABASE"]["PORT"]}/'

        return self.__sql_alchemy_server_uri

    @property
    def sql_alchemy_database_ssl(self):
        """sql alchemy database ssl, key property get

        :return dict (sql alchemy database ssl)
        :raise ValueError exception
        """
        if self.__sql_alchemy_database_ssl is None:
            self.__sql_alchemy_database_ssl = self.__server_config_file["SQL_ALCHEMY_DATABASE"]["SSL"]

        return self.__sql_alchemy_database_ssl

    @property
    def sql_alchemy_full_uri(self):
        """sql alchemy full uri, key property get

        :return string (sql alchemy full uri)
        :raise ValueError exception
        """
        if len(self.__sql_alchemy_full_uri) == 0:
            ssl_str = '?ssl=true' if self.sql_alchemy_database_ssl is True else ''

            self.__sql_alchemy_full_uri = f'{self.sql_alchemy_server_uri}{self.sql_alchemy_database_name}{ssl_str}'
        return self.__sql_alchemy_full_uri

    @property
    def main_database_data(self):
        """main database data key property get

        :return dict (main database data dict)
        :raise ValueError exception
        """
        if len(self.__main_database_data.items()) == 0:
            error_env_msgs = []

            main_database_user = os.environ.get(self.__server_config_file['SQL_ALCHEMY_DATABASE']['USER_ENV_VAR'])
            if main_database_user is None:
                error_env_msgs.append(f"Environment variable "
                                      f"'{self.__server_config_file['SQL_ALCHEMY_DATABASE']['USER_ENV_VAR']} not provided")

            main_database_password = os.environ.get(
                self.__server_config_file['SQL_ALCHEMY_DATABASE']['PASSWORD_ENV_VAR'])
            if main_database_password is None:
                error_env_msgs.append(f"Environment variable {self.__server_config_file['SQL_ALCHEMY_DATABASE']['PASSWORD_ENV_VAR']} not provided")

            if len(error_env_msgs) > 0:
                raise ValueError("\n".join(error_env_msgs))

            # Deepcopy
            self.__main_database_data = deepcopy(self.__server_config_file['SQL_ALCHEMY_DATABASE'])
            # Set user and password keys
            self.__main_database_data['USER'] = main_database_user
            self.__main_database_data['PASSWORD'] = main_database_password
            # Removing construction keys
            del self.__main_database_data['USER_ENV_VAR']
            del self.__main_database_data['PASSWORD_ENV_VAR']

        return self.__main_database_data

    @property
    def logging_database_data(self):
        """logging database data key property get

        :return dict (logging database data dict)
        :raise ValueError exception
        """
        if len(self.__logging_database_data.items()) == 0:
            error_env_msgs = []

            logging_database_user = os.environ.get(self.__server_config_file['LOGGING_DATABASE']['USER_ENV_VAR'])
            if logging_database_user is None:
                error_env_msgs.append(f"Environment variable "
                                      f"'{self.__server_config_file['LOGGING_DATABASE']['USER_ENV_VAR']} not provided")

            logging_database_password = os.environ.get(self.__server_config_file['LOGGING_DATABASE']['PASSWORD_ENV_VAR'])
            if logging_database_password is None:
                error_env_msgs.append(f"Environment variable "
                                      f"'{self.__server_config_file['LOGGING_DATABASE']['PASSWORD_ENV_VAR']} not provided")

            if len(error_env_msgs) > 0:
                raise ValueError("\n".join(error_env_msgs))

            # Deepcopy
            self.__logging_database_data = deepcopy(self.__server_config_file['LOGGING_DATABASE'])
            # Set user and password keys
            self.__logging_database_data['USER'] = logging_database_user
            self.__logging_database_data['PASSWORD'] = logging_database_password
            # Removing construction keys
            del self.__logging_database_data['USER_ENV_VAR']
            del self.__logging_database_data['PASSWORD_ENV_VAR']

        return self.__logging_database_data

    @property
    def logging_database_name(self):
        """logging database name, key property get

        :return string (logging database name)
        :raise ValueError exception
        """
        if len(self.__logging_database_name) == 0:
            self.__logging_database_name = self.logging_database_data['DATABASE_NAME']
        return self.__logging_database_name

    @property
    def secret_key(self):
        """secret key, key property get

        :return string (secret key)
        :raise ValueError exception
        """
        if len(self.__secret_key) == 0:
            secret_key = os.environ.get(self.__server_config_file['SECRET_KEY_ENV_VAR'])
            if secret_key is None:
                raise ValueError(f"Environment variable {self.__server_config_file['SECRET_KEY_ENV_VAR']} not provided")

            self.__secret_key = secret_key
        return self.__secret_key

    def get_flask_config_dict(self):
        """  Generate flask config dictionary
            :return flask_config_dict (dict)
        """
        # Deepcopy of config file
        flask_config_dict = deepcopy(self.__server_config_file)

        # Set sql alchemy uri
        flask_config_dict.update({"SQLALCHEMY_DATABASE_URI": self.sql_alchemy_full_uri})
        # Set logging database data
        flask_config_dict.update({"LOGGING_DATABASE": self.logging_database_data})
        # Set Secret key
        flask_config_dict.update({"SECRET_KEY": self.secret_key})

        # Removing keys to retrieve environment variables
        del flask_config_dict['SQL_ALCHEMY_DATABASE']
        del flask_config_dict['SECRET_KEY_ENV_VAR']

        return flask_config_dict
