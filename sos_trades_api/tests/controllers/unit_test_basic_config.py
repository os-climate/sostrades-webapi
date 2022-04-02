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
import os
from os.path import join, dirname
from dotenv import load_dotenv
from sos_trades_api import __file__ as root_file
from tempfile import gettempdir
import uuid
import json


# -----------------------------------------------------------------------------
# Modify configuration file for test purpose
# As the test can be launch simultaneously, having the same target database can drive to
# concurrent access.
# The objective here is to create a new configuration file with a dedicated database name
# for this test run

if os.environ.get('SOS_TRADES_SERVER_CONFIGURATION') is None:
    print('Server configuration not found. Loading of default developer configuration')

    dotenv_path = join(dirname(root_file), '..', '.flaskenv_unittest')
    print(dotenv_path)
    load_dotenv(dotenv_path)


if os.environ.get('SOS_TRADES_SERVER_CONFIGURATION') is None:
    raise ValueError('Cannot find mandatory environment variable to get server configuration')

configuration_filepath = os.environ['SOS_TRADES_SERVER_CONFIGURATION']
configuration_data = None
with open(configuration_filepath) as server_conf_file:
    configuration_data = json.load(server_conf_file)

# Get the current database name and add a random part
test_database_name = f"{configuration_data['SQL_ALCHEMY_DATABASE']['DATABASE_NAME']}-{str(uuid.uuid4())[:8]}"

# Overwrite test database name
configuration_data['SQL_ALCHEMY_DATABASE']['DATABASE_NAME'] = test_database_name

# Save the new configuration (without overwrite the original one) and change the
# associated environment variable
test_configuration_file = join(gettempdir(), f'test_configuration-{str(uuid.uuid4())}.json')
with open(test_configuration_file, 'w') as outfile:
    json.dump(configuration_data, outfile)

# Set base path
os.environ['SOS_TRADES_SERVER_CONFIGURATION'] = test_configuration_file
#os.environ['SAML_V2_METADATA_FOLDER'] = join(dirname(root_file), os.environ['SAML_V2_METADATA_FOLDER'])

os.environ['SOS_TRADES_DATA'] = os.path.join(
    gettempdir(), 'unit_test_persistance')
os.environ['SOS_TRADES_REFERENCES'] = os.path.join(
    gettempdir(), 'unit_test_persistance', 'references')

print(f'Configuration file used for test: {test_configuration_file}')
print(f'Database used for test: {test_database_name}')

import unittest
import sqlalchemy
from flask_migrate import Migrate, upgrade
from builtins import classmethod
from sos_trades_api.config import Config


config = Config()

database_server_uri = config.sql_alchemy_server_uri
database_name = config.sql_alchemy_database_name
log_database_name = config.logging_database_name

# Create SSL argument
ssl_arguments = {"ssl": config.sql_alchemy_database_ssl}
print(f'SSL configuration {ssl_arguments}')


class DatabaseUnitTestConfiguration(unittest.TestCase):
    """ Base class for make test based on SoSTrades database
    """

    app = None
    db = None

    @classmethod
    def setUpClass(cls):
        '''
        Create a database for the tests
        '''

        print('/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\')
        print(f'Start test of class {cls}')

        # Clean Database in case of previously bad issues
        DatabaseUnitTestConfiguration.tearDownClass()

        # 'IF NOT EXISTS' instruction is MySql/MariaDB specific
        create_database_sql_request = f'create database IF NOT EXISTS `{database_name}`;'
        create_log_database_sql_request = f'create database IF NOT EXISTS `{log_database_name}`;'
        use_database_sql_request = f'USE `{database_name}`;'

        # Create server connection
        engine = sqlalchemy.create_engine(
            database_server_uri, connect_args=ssl_arguments)

        with engine.connect() as connection:
            # Create database schema if not exist
            connection.execute(create_database_sql_request)

            # Create log database schema if not exist
            connection.execute(create_log_database_sql_request)

            # Select by default this database to perform further request
            connection.execute(use_database_sql_request)

        # Now initialize database using SQLAlchemy ORM
        from sos_trades_api.base_server import db, app

        DatabaseUnitTestConfiguration.app = app
        DatabaseUnitTestConfiguration.db = db

        with DatabaseUnitTestConfiguration.app.app_context():

            migrate = Migrate(DatabaseUnitTestConfiguration.app,
                              DatabaseUnitTestConfiguration.db)

            # get the migration folder
            migration_folder = os.path.join(os.path.dirname(
                os.path.dirname(root_file)), 'migrations')
            upgrade(directory=migration_folder)

            from sos_trades_api.controllers.sostrades_data.user_controller import create_test_user_account
            create_test_user_account()

    @classmethod
    def tearDownClass(cls):
        '''
        Drop database used for tests
        '''

        # 'IF EXISTS' instruction is MySql/MariaDB specific
        drop_database_sql_request = f'drop database IF EXISTS `{database_name}`;'
        drop_log_database_sql_request = f'drop database IF EXISTS `{log_database_name}`;'

        # Create server connection
        engine = sqlalchemy.create_engine(
            database_server_uri, connect_args=ssl_arguments)

        with engine.connect() as connection:
            # Create database schema if not exist
            connection.execute(drop_database_sql_request)

            # Create log database schema if not exist
            connection.execute(drop_log_database_sql_request)

        print(f'End test of class {cls}')
        print('/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\')

    def setUp(self):
        print('-----------------------------------------------------------')
        print(f'Start test method {self._testMethodName}')

    def tearDown(self):
        print(f'End test method {self._testMethodName}')
        print('-----------------------------------------------------------')
