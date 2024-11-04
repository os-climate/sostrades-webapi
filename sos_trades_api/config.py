'''
Copyright 2022 Airbus SAS
Modifications on 2023/11/24 Copyright 2023 Capgemini

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
import os
from builtins import property
from copy import deepcopy
from os.path import abspath, dirname, join
from pathlib import Path

"""
Flask and database configuration variable
"""

BASEDIR = abspath(dirname(__file__))

# pylint: disable=line-too-long
# pylint: disable=too-many-instance-attributes


class Config:
    """
    Flask configuration class

    Flask and database configuration variable only used for development environment
    Production environment is overwritten using an external configuration
    file
    """

    #
    # FLASK CONFIGURATION SECTION END
    # Environment configuration variable names
    CONFIG_EXECUTION_STRATEGY = "SOS_TRADES_EXECUTION_STRATEGY"  # for values : 'subprocess', 'kubernetes'
    CONFIG_EXECUTION_STRATEGY_THREAD = "thread"
    CONFIG_EXECUTION_STRATEGY_SUBPROCESS = "subprocess"
    CONFIG_EXECUTION_STRATEGY_K8S = "kubernetes"

    CONFIG_SERVER_MODE = "SOS_TRADES_SERVER_MODE"
    CONFIG_SERVER_MODE_K8S = "kubernetes"
    CONFIG_SERVER_MODE_MONO = "mono"
    CONFIG_MANIFESTS_FOLDER_PATH = "MANIFESTS_FOLDER_PATH"
    CONFIG_DEPLOYMENT_STUDY_SERVER_FILE_NAME = "deployment_study_case_server.yml.jinja"
    CONFIG_SERVICE_STUDY_SERVER_FILE_NAME = "service_study_case_server.yml.jinja"

    CONFIG_DATA_ROOT_DIR = "SOS_TRADES_DATA"
    CONFIG_REFERENCE_ROOT_DIR = "SOS_TRADES_REFERENCES"
    CONFIG_EEB_CONFIGURATION_FILE = "EEB_PATH"
    CONFIG_RSA_ROOT_DIR = "SOS_TRADES_RSA"

    CONFIG_STUDY_POD_DELAY = "SOS_TRADES_STUDY_POD_INACTIVATE_DELAY_HOUR"
    CONFIG_LOCAL_FOLDER_PATH = "SOS_TRADES_LOCAL_FOLDER"
    CONFIG_FLAVOR_KUBERNETES = "CONFIG_FLAVOR_KUBERNETES"
    CONFIG_ACTIVATE_POD_WATCHER = "ACTIVATE_POD_WATCHER"
    CONFIG_FLAVOR_POD_EXECUTION = "PodExec"

    def __init__(self):
        """
        Constructor
        """
        self.__server_config_file = {}

        self.__data_root_dir = ""
        self.__reference_root_dir = ""

        self.__available_strategies = [Config.CONFIG_EXECUTION_STRATEGY_THREAD,
                                       Config.CONFIG_EXECUTION_STRATEGY_SUBPROCESS,
                                       Config.CONFIG_EXECUTION_STRATEGY_K8S]
        self.__execution_strategy = ""

        self.__eeb_configuration_filepath = ""

        self.__manifests_folder_path = ""

        self.__available_server_modes = [Config.CONFIG_SERVER_MODE_K8S,
                                       Config.CONFIG_SERVER_MODE_MONO]

        self.__server_mode = ""

        self.__rsa_root_dir = ""

        self.__rsa_public_key = ""
        self.__rsa_private_key = ""

        self.__logging_database_connect_args = {}
        self.__logging_database_uri = None
        self.__logging_database_engine_options = {}
        self.__main_database_connect_args = {}
        self.__main_database_uri = None
        self.__main_database_engine_options = {}
        self.__secret_key = ""

        self.__study_pod_delay = None
        self.__local_folder_path = ""
        self.__kubernetes_flavor_for_study = None
        self.__kubernetes_flavor_for_exec = None

        if os.environ.get("SOS_TRADES_SERVER_CONFIGURATION") is not None:
            with open(os.environ["SOS_TRADES_SERVER_CONFIGURATION"]) as server_conf_file:
                self.__server_config_file = json.load(server_conf_file)
        else:
            raise Exception(
                'Environment variable "SOS_TRADES_SERVER_CONFIGURATION" not found')

    def check(self):
        """
        Make a check on mandatory parameter to make sure configuration is correct
        Each property is able to raise an exception if it cannot found the necessary
        information to initialize
        """
        # pylint: disable=unused-variable

        # -------------------------------------------------------------------
        # This first section check all mandatory data needs to run the server
        execution_strategy = self.execution_strategy
        server_mode = self.server_mode


        data_root_dir = self.data_root_dir
        reference_root_dir = self.reference_root_dir
        rsa_public_key_file = self.rsa_public_key_file
        rsa_private_key_file = self.rsa_private_key_file

        eeb_filepath = self.eeb_filepath

        manifest_folder_path = self.manifests_folder_path

        if self.server_mode == self.CONFIG_SERVER_MODE_K8S:
            deployment_study_server_filepath = self.deployment_study_server_filepath
            service_study_server_filepath = self.service_study_server_filepath

            kubernetes_flavor_config_for_study = self.kubernetes_flavor_config_for_study
            kubernetes_flavor_config_for_exec = self.kubernetes_flavor_config_for_exec
        # pylint: enable=unused-variable

    @property
    def data_root_dir(self):
        """
        data root directory property get
        not mandatory

        :return string (folder path)
        :raise ValueError exception
        """
        if len(self.__data_root_dir) == 0:
            if self.__server_config_file.get(self.CONFIG_DATA_ROOT_DIR) is None:
                raise ValueError(
                    f"Configuration variable '{self.CONFIG_DATA_ROOT_DIR}' not provided")

            if not Path(self.__server_config_file.get(self.CONFIG_DATA_ROOT_DIR)).exists():
                try:
                    os.makedirs(self.__server_config_file.get(self.CONFIG_DATA_ROOT_DIR), exist_ok=True)
                except Exception as error:
                    raise ValueError(
                        f"Configuration variable '{self.CONFIG_DATA_ROOT_DIR}' values is not a valid folder path : {self.__server_config_file.get(self.CONFIG_DATA_ROOT_DIR)}\n{error}")

            self.__data_root_dir = self.__server_config_file.get(self.CONFIG_DATA_ROOT_DIR)

        return self.__data_root_dir

    @property
    def reference_root_dir(self):
        """
        reference data root directory property get

        :return string (folder path)
        :raise ValueError exception
        """
        if len(self.__reference_root_dir) == 0:
            if self.__server_config_file.get(self.CONFIG_REFERENCE_ROOT_DIR) is None:
                raise ValueError(
                    f"Configuration variable '{self.CONFIG_REFERENCE_ROOT_DIR}' not provided")

            if not Path(self.__server_config_file.get(self.CONFIG_REFERENCE_ROOT_DIR)).exists():
                try:
                    os.makedirs(self.__server_config_file.get(self.CONFIG_REFERENCE_ROOT_DIR), exist_ok=True)
                except Exception as error:
                    raise ValueError(
                        f"Configuration variable '{self.CONFIG_REFERENCE_ROOT_DIR}' values is not a valid folder path : {self.__server_config_file.get(self.CONFIG_REFERENCE_ROOT_DIR)}\n{error}")

            self.__reference_root_dir = self.__server_config_file.get(self.CONFIG_REFERENCE_ROOT_DIR)

        return self.__reference_root_dir

    @property
    def execution_strategy(self):
        """
        execution strategy property get

        :return string ('thread', 'subprocess', 'kubernetes')
        :raise ValueError exception
        """
        if len(self.__execution_strategy) == 0:
            if self.__server_config_file.get(self.CONFIG_EXECUTION_STRATEGY) is None:
                raise ValueError(
                    f"Configuration variable '{self.CONFIG_EXECUTION_STRATEGY}' not provided")

            if not len(self.__server_config_file.get(self.CONFIG_EXECUTION_STRATEGY)) > 0:
                raise ValueError(
                    f"Configuration variable '{self.CONFIG_EXECUTION_STRATEGY}' has no value, any of the following is intended : {self.__available_strategies}")

            if self.__server_config_file.get(self.CONFIG_EXECUTION_STRATEGY) not in self.__available_strategies:
                raise ValueError(
                    f"Configuration variable '{self.CONFIG_EXECUTION_STRATEGY}' value is unknown, any of the following is intended : {self.__available_strategies}")

            self.__execution_strategy = self.__server_config_file.get(self.CONFIG_EXECUTION_STRATEGY)

        return self.__execution_strategy

    @property
    def manifests_folder_path(self):
        """
        manifests folder kubernetes configuration property get

        :return string (filepath)
        :raise ValueError exception
        """
        if len(self.__manifests_folder_path) == 0 and self.server_mode == self.CONFIG_SERVER_MODE_K8S:
            if self.__server_config_file.get(self.CONFIG_MANIFESTS_FOLDER_PATH) is None:
                raise ValueError(
                    f"Configuration variable '{self.CONFIG_MANIFESTS_FOLDER_PATH}' not provided")

            if not Path(self.__server_config_file.get(self.CONFIG_MANIFESTS_FOLDER_PATH)).exists():
                raise ValueError(
                    f"Configuration variable '{self.CONFIG_MANIFESTS_FOLDER_PATH}' values for study server deployment is not a valid filepath : {self.__server_config_file.get(self.CONFIG_MANIFESTS_FOLDER_PATH)}")

            self.__manifests_folder_path = self.__server_config_file.get(self.CONFIG_MANIFESTS_FOLDER_PATH)

        return self.__manifests_folder_path

    @property
    def service_study_server_filepath(self):
        """
        service_study_server manifest file path property get

        :return string (filepath)
        :raise ValueError exception
        """
        file_path =  ""
        if self.server_mode == self.CONFIG_SERVER_MODE_K8S:
            file_path = join(self.manifests_folder_path, Config.CONFIG_SERVICE_STUDY_SERVER_FILE_NAME)
            if not Path(file_path).exists():
                raise ValueError(
                    f"Manifest of the study case server service '{Config.CONFIG_SERVICE_STUDY_SERVER_FILE_NAME}' is not at the location : {file_path}")

        return file_path

    @property
    def deployment_study_server_filepath(self):
        """
        deployment_study_server manifest file path property get

        :return string (filepath)
        :raise ValueError exception
        """
        file_path =  ""
        if self.server_mode == self.CONFIG_SERVER_MODE_K8S:
            file_path = join(self.manifests_folder_path, Config.CONFIG_DEPLOYMENT_STUDY_SERVER_FILE_NAME)
            if not Path(file_path).exists():
                raise ValueError(
                    f"Manifest of the study case server deployment '{Config.CONFIG_DEPLOYMENT_STUDY_SERVER_FILE_NAME}' is not at the location : {file_path}")

        return file_path


    @property
    def eeb_filepath(self):
        """
        execution engine block kubernets configuration property get

        :return string (filepath)
        :raise ValueError exception
        """
        if len(self.__eeb_configuration_filepath) == 0 and self.execution_strategy == self.CONFIG_EXECUTION_STRATEGY_K8S:
            if self.__server_config_file.get(self.CONFIG_EEB_CONFIGURATION_FILE) is None:
                raise ValueError(
                    f"Configuration variable '{self.CONFIG_EEB_CONFIGURATION_FILE}' not provided")

            if not Path(self.__server_config_file.get(self.CONFIG_EEB_CONFIGURATION_FILE)).exists():
                raise ValueError(
                    f"Configuration variable '{self.CONFIG_EEB_CONFIGURATION_FILE}' values is not a valid filepath : {self.__server_config_file.get(self.CONFIG_EEB_CONFIGURATION_FILE)}")

            self.__eeb_configuration_filepath = self.__server_config_file.get(self.CONFIG_EEB_CONFIGURATION_FILE)

        return self.__eeb_configuration_filepath

    @property
    def server_mode(self):
        """
        server_mode property get

        :return string ('split', 'mono')
        :raise ValueError exception
        """
        if len(self.__server_mode) == 0:
            if self.__server_config_file.get(self.CONFIG_SERVER_MODE) is None:
                raise ValueError(
                    f"Configuration variable '{self.CONFIG_SERVER_MODE}' not provided")

            if not len(self.__server_config_file.get(self.CONFIG_SERVER_MODE)) > 0:
                raise ValueError(
                    f"Configuration variable '{self.CONFIG_SERVER_MODE}' has no value, any of the following is intended : {self.__available_server_modes}")

            if self.__server_config_file.get(self.CONFIG_SERVER_MODE) not in self.__available_server_modes:
                raise ValueError(
                    f"Configuration variable '{self.CONFIG_SERVER_MODE}' value is unknown, any of the following is intended : {self.__available_server_modes}")

            self.__server_mode = self.__server_config_file.get(self.CONFIG_SERVER_MODE)

        return self.__server_mode

    @property
    def rsa_public_key_file(self):
        """
        rsa public key property get

        :return string (filepath)
        :raise ValueError exception
        """
        if len(self.__rsa_public_key) == 0:
            if self.__server_config_file.get(self.CONFIG_RSA_ROOT_DIR) is not None:
                if not Path(self.__server_config_file.get(self.CONFIG_RSA_ROOT_DIR)).exists():
                    raise ValueError(
                        f"Configuration variable '{self.CONFIG_RSA_ROOT_DIR}' values is not a valid folder : {self.__server_config_file.get(self.CONFIG_RSA_ROOT_DIR)}")

                if not Path(join(self.__server_config_file.get(self.CONFIG_RSA_ROOT_DIR), "public_key.pem")).exists():
                    raise ValueError(
                        f"Public rsa key not found at the specified filepath: {join(self.__server_config_file.get(self.CONFIG_RSA_ROOT_DIR), 'public_key.pem')}")

                self.__rsa_public_key = join(self.__server_config_file.get(self.CONFIG_RSA_ROOT_DIR), "public_key.pem")

        return self.__rsa_public_key

    @property
    def rsa_private_key_file(self):
        """
        rsa private key property get

        :return string (filepath)
        :raise ValueError exception
        """
        if len(self.__rsa_private_key) == 0:
            if self.__server_config_file.get(self.CONFIG_RSA_ROOT_DIR) is not None:

                if not Path(self.__server_config_file.get(self.CONFIG_RSA_ROOT_DIR)).exists():
                    raise ValueError(
                        f"Configuration variable '{self.CONFIG_RSA_ROOT_DIR}' values is not a valid folder : {self.__server_config_file.get(self.CONFIG_RSA_ROOT_DIR)}")

                if not Path(join(self.__server_config_file.get(self.CONFIG_RSA_ROOT_DIR), "private_key.pem")).exists():
                    raise ValueError(
                        f"Private rsa key not found at the specified filepath: {join(self.__server_config_file.get(self.CONFIG_RSA_ROOT_DIR), 'private_key.pem')}")

                self.__rsa_private_key = join(self.__server_config_file.get(self.CONFIG_RSA_ROOT_DIR), "private_key.pem")

        return self.__rsa_private_key

    @property
    def study_pod_delay(self):
        """
        study pod delay (get)
        mandatory in kuberneted server mode
        Give the delay to keep a study pod inactive befor truning it down
        Necessary only in kuberneted server mode

        :return float
        :raise ValueError exception
        """
        if self.__study_pod_delay is None:
            if self.__server_config_file.get(self.CONFIG_STUDY_POD_DELAY) is not None:
                self.__study_pod_delay = self.__server_config_file.get(self.CONFIG_STUDY_POD_DELAY)

        return self.__study_pod_delay

    @property
    def local_folder_path(self):
        """
        local folder path (get)
        Give the path to the local folder (usefull in micro-service mode)
        Used to store the file with the study last alive date

        :return string
        :raise ValueError exception
        """
        if self.__local_folder_path == "":
            if self.__server_config_file.get(self.CONFIG_LOCAL_FOLDER_PATH) is not None:
                self.__local_folder_path = self.__server_config_file.get(self.CONFIG_LOCAL_FOLDER_PATH)
                if not Path(self.__server_config_file.get(self.CONFIG_LOCAL_FOLDER_PATH)).exists():
                    try:
                        os.makedirs(self.__server_config_file.get(self.CONFIG_LOCAL_FOLDER_PATH), exist_ok=True)
                    except Exception as error:
                        raise ValueError(
                            f"Configuration variable '{self.CONFIG_LOCAL_FOLDER_PATH}' values is not a valid folder path : {self.__server_config_file.get(self.CONFIG_LOCAL_FOLDER_PATH)}\n{error}")

        return self.__local_folder_path

    @property
    def main_database_connect_args(self):
        """
        sql alchemy database connect args key property get

        :return dict (sql alchemy database connect args dict)
        :raise ValueError exception
        """
        if len(self.__main_database_connect_args.items()) == 0:
            self.__main_database_connect_args = self.__server_config_file['SQL_ALCHEMY_DATABASE']['CONNECT_ARGS']

        return self.__main_database_connect_args

    @property
    def main_database_uri(self):
        """
        sql alchemy full uri, key property get

        :return string (sql alchemy full uri)
        :raise ValueError exception
        """
        if self.__main_database_uri is None:
            database_uri_not_formatted = self.__server_config_file['SQL_ALCHEMY_DATABASE']['URI']

            # Retrieve env vars
            uri_env_vars = self.__server_config_file['SQL_ALCHEMY_DATABASE']['URI_ENV_VARS']
            uri_format_env_vars = {
                key: os.environ.get(env_var) for key, env_var in uri_env_vars.items()
            }
            # Check if env vars are set
            none_vars = {var_name for var_name, var_value in uri_format_env_vars.items() if var_value is None}
            if len(none_vars) > 0:
                error_env_msg = "\n".join(
                    [
                        f"Main database : Environment variable for {var_name} not provided"
                        for var_name in none_vars
                    ]
                )
                raise ValueError(error_env_msg)
            
            try:
                self.__main_database_uri = database_uri_not_formatted.format(**uri_format_env_vars)
            except KeyError as e:
                raise ValueError("Main database : Unable to format connection string, some parameters are missing in URI_ENV_VARS") from e
        return self.__main_database_uri
    
    @property
    def main_database_engine_options(self):
        """
        main database engine options key property get

        :return dict (main database engine options dict)
        :raise ValueError exception
        """
        if len(self.__main_database_engine_options.items()) == 0:
            if 'ENGINE_OPTIONS' in self.__server_config_file['SQL_ALCHEMY_DATABASE']:
                self.__main_database_engine_options = self.__server_config_file['SQL_ALCHEMY_DATABASE']['ENGINE_OPTIONS']
            else:
                self.__main_database_engine_options = {}

        return self.__main_database_engine_options

    @property
    def logging_database_connect_args(self):
        """
        logging database connect args key property get

        :return dict (logging database connect args dict)
        :raise ValueError exception
        """
        if len(self.__logging_database_connect_args.items()) == 0:
            self.__logging_database_connect_args = self.__server_config_file['LOGGING_DATABASE']['CONNECT_ARGS']

        return self.__logging_database_connect_args

    @property
    def logging_database_uri(self):
        """logging database uri, key property get

        :return string
        :raise ValueError exception
        """
        if self.__logging_database_uri is None:
            database_uri_not_formatted = self.__server_config_file['LOGGING_DATABASE']['URI']

            # Retrieve env vars
            uri_env_vars = self.__server_config_file['LOGGING_DATABASE']['URI_ENV_VARS']
            uri_format_env_vars = {
                key: os.environ.get(env_var) for key, env_var in uri_env_vars.items()
            }
            # Check if env vars are set
            none_vars = {var_name for var_name, var_value in uri_format_env_vars.items() if var_value is None}
            if len(none_vars) > 0:
                error_env_msg = "\n".join(
                    [
                        f"Logging database : Environment variable for {var_name} not provided"
                        for var_name in none_vars
                    ]
                )
                raise ValueError(error_env_msg)
            
            try:
                self.__logging_database_uri = database_uri_not_formatted.format(**uri_format_env_vars)
            except KeyError as e:
                raise ValueError("Logging database : Unable to format connection string, some parameters are missing in URI_ENV_VARS") from e
        return self.__logging_database_uri
    
    @property
    def logging_database_engine_options(self):
        """
        logging database engine options key property get

        :return dict (logging database engine options dict)
        :raise ValueError exception
        """
        if len(self.__logging_database_engine_options.items()) == 0:
            if 'ENGINE_OPTIONS' in self.__server_config_file['LOGGING_DATABASE']:
                self.__logging_database_engine_options = self.__server_config_file['LOGGING_DATABASE']['ENGINE_OPTIONS']
            else:
                self.__logging_database_engine_options = {}

        return self.__logging_database_engine_options

    @property
    def secret_key(self):
        """
        secret key, key property get

        :return string (secret key)
        :raise ValueError exception
        """
        if len(self.__secret_key) == 0:
            secret_key = os.environ.get(self.__server_config_file["SECRET_KEY_ENV_VAR"])
            if secret_key is None:
                raise ValueError(f"Environment variable {self.__server_config_file['SECRET_KEY_ENV_VAR']} not provided")

            self.__secret_key = secret_key
        return self.__secret_key

    def get_flask_config_dict(self):
        """
        Generate flask config dictionary
        :return flask_config_dict (dict)
        """
        # Deepcopy of config file
        flask_config_dict = deepcopy(self.__server_config_file)

        # Set sql alchemy uri
        flask_config_dict.update({"SQLALCHEMY_DATABASE_URI": self.main_database_uri})
        flask_config_dict.update({"SQLALCHEMY_ENGINE_OPTIONS": {'connect_args': self.main_database_connect_args}})
        # Set Secret key
        flask_config_dict.update({"SECRET_KEY": self.secret_key})

        # Key for Ontology grace period
        flask_config_dict.update({"ONTOLOGY_GRACE_PERIOD": None})

        # Removing keys to retrieve environment variables
        del flask_config_dict["SQL_ALCHEMY_DATABASE"]
        del flask_config_dict["SECRET_KEY_ENV_VAR"]

        return flask_config_dict

    @property
    def kubernetes_flavor_config_for_study(self):
        """
        Retrieve Kubernetes flavor configuration from server config.
        
        :return: A dictionary containing Kubernetes flavor configuration.
        :rtype: dict
        :raises KeyError: If CONFIG_FLAVOR_KUBERNETES key is not found. If Kubernetes flavor configuration is not valid.
        """
        if self.__kubernetes_flavor_for_study is None and self.server_mode == self.CONFIG_SERVER_MODE_K8S:

            if self.CONFIG_FLAVOR_KUBERNETES not in self.__server_config_file:
                raise KeyError("CONFIG_FLAVOR_KUBERNETES is not in configuration file")

            kubernetes_flavor = self.__server_config_file[self.CONFIG_FLAVOR_KUBERNETES]

            if "PodStudy" not in kubernetes_flavor.keys():
                raise KeyError("PodStudy is not in CONFIG_FLAVOR_KUBERNETES")

            self.__validate_flavor(kubernetes_flavor["PodStudy"])

            self.__kubernetes_flavor_for_study = self.__sort_flavors(kubernetes_flavor["PodStudy"])

        return self.__kubernetes_flavor_for_study


    @property
    def kubernetes_flavor_config_for_exec(self):
        """
        Retrieve Kubernetes flavor configuration from server config.
        
        :return: A dictionary containing Kubernetes flavor configuration.
        :rtype: dict
        :raises KeyError: If CONFIG_FLAVOR_KUBERNETES key is not found. If Kubernetes flavor configuration is not valid.
        """
        if self.__kubernetes_flavor_for_exec is None and self.execution_strategy == self.CONFIG_EXECUTION_STRATEGY_K8S:
            if self.CONFIG_FLAVOR_KUBERNETES not in self.__server_config_file:
                raise KeyError("CONFIG_FLAVOR_KUBERNETES is not in configuration file")

            kubernetes_flavor = self.__server_config_file[self.CONFIG_FLAVOR_KUBERNETES]

            if self.CONFIG_FLAVOR_POD_EXECUTION not in kubernetes_flavor.keys():
                raise KeyError("PodExec is not in CONFIG_FLAVOR_KUBERNETES")

            self.__validate_flavor(kubernetes_flavor[self.CONFIG_FLAVOR_POD_EXECUTION])

            self.__kubernetes_flavor_for_exec = self.__sort_flavors(kubernetes_flavor[self.CONFIG_FLAVOR_POD_EXECUTION])

        return self.__kubernetes_flavor_for_exec

    @staticmethod
    def __validate_flavor(list_flavors:dict):
        """
        Validate Kubernetes flavor configuration.

        :param config: Kubernetes flavor configuration.
        :type config: dict
        :raises ValueError: If Kubernetes flavor configuration is not valid.
        """
        if not isinstance(list_flavors, dict):
            raise ValueError("Kubernetes flavor configuration must be a dictionary")


        # Iterate through each flavor
        for flavor, config in list_flavors.items():
            if not isinstance(config, dict):
                raise ValueError(f"Configuration for flavor '{flavor}' must be a dictionary")

            # Check if 'requests' and 'limits' are defined
            if "requests" not in config or "limits" not in config:
                raise ValueError(f"'requests' and 'limits' must be defined for flavor '{flavor}'")

            requests = config["requests"]
            limits = config["limits"]

            # Check if 'memory' and 'cpu' are defined under 'requests'
            if not isinstance(requests, dict) or "memory" not in requests or "cpu" not in requests:
                raise ValueError(f"'memory' and 'cpu' must be defined under 'requests' for flavor '{flavor}'")

            # Check if 'memory' and 'cpu' are defined under 'limits'
            if not isinstance(limits, dict) or "memory" not in limits or "cpu" not in limits:
                raise ValueError(f"'memory' and 'cpu' must be defined under 'limits' for flavor '{flavor}'")
        
    def __sort_flavors(self, flavors:dict)->dict:
        from sos_trades_api.tools.code_tools import (
            convert_byte_into_byte_unit_targeted,
            extract_number_and_unit,
        )
        """
        Sort the kubernetes flavors by memory limits and requests
        :param flavors: dict of flavors to sort
        :return: dict of flavors sorted by memory
        """
        def sort_by_memory(memory_limit, memory_request):
            """
            convert the memories in Mi and return them for sorted function
            """
            limit_value, limit_unit =  extract_number_and_unit(memory_limit)
            request_value, request_unit =  extract_number_and_unit(memory_request)
            limit_mi = convert_byte_into_byte_unit_targeted(limit_value, limit_unit, 'Mi')
            request_mi = convert_byte_into_byte_unit_targeted(request_value, request_unit, 'Mi')
            return (limit_mi, request_mi)

        sorted_dict = dict(sorted(flavors.items(), key=lambda item:sort_by_memory(item[1]['limits']["memory"], item[1]['requests']["memory"])))
        return sorted_dict
        

    @property
    def pod_watcher_activated(self):
        return self.__server_config_file.get(self.CONFIG_ACTIVATE_POD_WATCHER, False)
