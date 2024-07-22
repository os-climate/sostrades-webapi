'''
Copyright 2022 Airbus SAS
Modifications on 2024/06/07-2024/06/13 Copyright 2024 Capgemini
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
import uuid
from os.path import dirname, join
from tempfile import gettempdir

from dotenv import load_dotenv
from sqlalchemy.engine.url import make_url

from sos_trades_api import __file__ as root_file

# -----------------------------------------------------------------------------
# Modify configuration file for test purpose
# As the test can be launch simultaneously, having the same target database can drive to
# concurrent access.
# The objective here is to create a new configuration file with a dedicated database name
# for this test run

if os.environ.get("SOS_TRADES_SERVER_CONFIGURATION") is None:
    print("Server configuration not found. Loading of default developer configuration")

    dotenv_path = join(dirname(root_file), "..", ".flaskenv_unittest")
    print(dotenv_path)
    load_dotenv(dotenv_path)


if os.environ.get("SOS_TRADES_SERVER_CONFIGURATION") is None:
    raise ValueError("Cannot find mandatory environment variable to get server configuration")

configuration_filepath = os.environ["SOS_TRADES_SERVER_CONFIGURATION"]
configuration_data = None
with open(configuration_filepath) as server_conf_file:
    configuration_data = json.load(server_conf_file)

# Get the current database name and add a random part
unique_identifier = str(uuid.uuid4())[:8]
def append_suffix_to_database_uri(database_uri:str, suffix:str) -> str:
    """
    Appends a suffix to the database name in the URI.

    Args:
        database_uri (str): The original database URI.
        suffix (str): The suffix to append to the database name.

    Returns:
        str: The updated database URI with the appended suffix.
    """
    url = make_url(database_uri)
    
    # Extract the current database name
    database_name = url.database

    if database_name.endswith(".db"):
        database_name = database_name[:-3]
        return database_uri.replace(database_name, database_name + suffix)
    elif database_name.endswith(".sqlite"):
        database_name = database_name[:-7]
        return database_uri.replace(database_name, database_name + suffix)
    else:
        return database_uri.replace(database_name, database_name + suffix)

test_database_uri = append_suffix_to_database_uri(configuration_data['SQL_ALCHEMY_DATABASE']['URI'], f"-{unique_identifier}")
test_log_database_uri = append_suffix_to_database_uri(configuration_data['LOGGING_DATABASE']['URI'], f"-{unique_identifier}")

# Overwrite test database name
configuration_data["SQL_ALCHEMY_DATABASE"]["URI"] = test_database_uri
configuration_data["LOGGING_DATABASE"]["URI"] = test_log_database_uri

# Save the new configuration (without overwrite the original one) and change the
# associated environment variable
test_configuration_file = join(gettempdir(), f"test_configuration-{uuid.uuid4()!s}.json")
with open(test_configuration_file, "w") as outfile:
    json.dump(configuration_data, outfile)

# Set base path
os.environ["SOS_TRADES_SERVER_CONFIGURATION"] = test_configuration_file
#os.environ['SAML_V2_METADATA_FOLDER'] = join(dirname(root_file), os.environ['SAML_V2_METADATA_FOLDER'])

print(f"Configuration file used for test: {test_configuration_file}")
print(f"Database URI used for test: {test_database_uri}")
print(f"Database URI used for test log: {test_log_database_uri}")

# ruff: noqa: E402
import sqlite3
import unittest
from builtins import classmethod

import sqlalchemy
from flask_migrate import Migrate, upgrade
from sqlalchemy import text

from sos_trades_api.config import Config


def delete_everything_from_database(db_path):
    """
    Deletes all tables from the specified SQLite database.

    Args:
        db_path (str): Path to the SQLite database file.
    """
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Fetch all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    # Drop all tables
    for table_name in tables:
        if table_name[0] != "sqlite_sequence":
            cursor.execute(f'DROP TABLE IF EXISTS "{table_name[0]}";')

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

config = Config()

database_server_uri = config.sql_alchemy_full_uri
database_server_url = make_url(database_server_uri)
logging_database_server_uri = config.logging_database_uri
logging_database_server_url = make_url(logging_database_server_uri)
connect_args = config.sql_alchemy_connect_args


class DatabaseUnitTestConfiguration(unittest.TestCase):
    """
    Base class for make test based on SoSTrades database
    """

    app = None
    db = None

    @classmethod
    def setUpClass(cls):
        """
        Create a database for the tests
        """
        # Clean Database in case of previously bad issues
        DatabaseUnitTestConfiguration.tearDownClass()

        # Determine the database type
        is_sqlite = database_server_url.get_backend_name() == 'sqlite'
        
        if not is_sqlite:
            # 'IF NOT EXISTS' instruction is MySql/MariaDB specific
            create_database_sql_request = text(f"create database IF NOT EXISTS `{database_server_url.database}`;")
            create_log_database_sql_request = text(f"create database IF NOT EXISTS `{logging_database_server_url.database}`;")
            use_database_sql_request = text(f"USE `{database_server_url.database}`;")

            # Create server connection
            engine = sqlalchemy.create_engine(database_server_uri, connect_args=connect_args)

            with engine.connect() as connection:
                # Create database schema if not exist
                connection.execute(create_database_sql_request)

                # Create log database schema if not exist
                connection.execute(create_log_database_sql_request)

                # Select by default this database to perform further request
                connection.execute(use_database_sql_request)

        # Now initialize database using SQLAlchemy ORM
        from sos_trades_api.server.base_server import app, db

        DatabaseUnitTestConfiguration.app = app
        DatabaseUnitTestConfiguration.db = db

        with DatabaseUnitTestConfiguration.app.app_context():

            migrate = Migrate(DatabaseUnitTestConfiguration.app,
                              DatabaseUnitTestConfiguration.db)

            # get the migration folder
            migration_folder = os.path.join(os.path.dirname(os.path.dirname(root_file)), "migrations")
            upgrade(directory=migration_folder)

            from sos_trades_api.controllers.sostrades_data.user_controller import (
                create_test_user_account,
            )
            create_test_user_account()

    @classmethod
    def tearDownClass(cls):
        """
        Drop database used for tests
        """
        
        # Determine the database type
        is_sqlite = database_server_url.get_backend_name() == 'sqlite'
        
        if not is_sqlite:
            # 'IF EXISTS' instruction is MySql/MariaDB specific
            drop_database_sql_request = text(f"drop database IF EXISTS `{database_server_url.database}`;")
            drop_log_database_sql_request = text(f"drop database IF EXISTS `{logging_database_server_url.database}`;")

            # Create server connection
            engine = sqlalchemy.create_engine(
                database_server_uri, connect_args=connect_args)

            with engine.connect() as connection:
                # Create database schema if not exist
                connection.execute(drop_database_sql_request)

                # Create log database schema if not exist
                connection.execute(drop_log_database_sql_request)
        else:
            delete_everything_from_database(database_server_url.database)
            delete_everything_from_database(logging_database_server_url.database)

    def setUp(self):
        pass

    def tearDown(self):
        pass
