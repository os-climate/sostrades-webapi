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
import sys
import traceback as tb
import click

from werkzeug.exceptions import HTTPException
from flask import json, jsonify
from flask import Flask, render_template, request
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from flask.helpers import send_from_directory
from flask.cli import with_appcontext

from sos_trades_api.config import Config


import logging
import os
from os.path import dirname, join


# Create  flask server and set local configuration

server_name = __name__
if os.environ.get('SERVER_NAME') is not None:
    server_name = os.environ['SERVER_NAME']

app = Flask(server_name)


# Env constant
PRODUCTION = 'PRODUCTION'
ENVIRONMENT = 'ENVIRONMENT'
UNIT_TEST = 'UNIT_TEST'

try:
    config = Config()
    flask_config_dict = config.get_flask_config_dict()
    app.config.update(flask_config_dict)

    # Register database on app
    db = SQLAlchemy()
    db.init_app(app)

    # As flask application and database are initialized, then import
    # sos_trades_api dependencies

    import sos_trades_api
    from sos_trades_api.tools.cache.study_case_cache import StudyCaseCache
    from sos_trades_api.tools.logger.application_mysql_handler import ApplicationMySQLHandler, ApplicationRequestFormatter
    from sos_trades_api.models.database_models import User, Group
    from sos_trades_api.models.custom_json_encoder import CustomJsonEncoder

    app_mysql_handler = ApplicationMySQLHandler(
        db=config.logging_database_data)
    app_mysql_handler.setFormatter(ApplicationRequestFormatter(
        "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"))
    app.logger.addHandler(app_mysql_handler)

    os.environ['FLASK_ENV'] = app.config['ENVIRONMENT']

    if os.environ['FLASK_ENV'] == PRODUCTION:
        logging.basicConfig(level=logging.INFO)

        # Remove all trace
        logging.getLogger('engineio.server').setLevel(51)
    else:
        logging.basicConfig(level=logging.INFO)
        app.logger.setLevel(logging.DEBUG)
        logging.getLogger('engineio.server').setLevel(logging.DEBUG)

    app.logger.info(
        f'{os.environ["FLASK_ENV"]} environment configuration loaded')

    # Test if SAML settings file path is filled
    if os.environ.get('SAML_V2_METADATA_FOLDER') is None:
        app.logger.info('SAML_V2_METADATA_FOLDER configuration not found, SSO will be disabled')
    else:
        app.logger.info('SAML_V2_METADATA_FOLDER environment variable found')

        # Check that the settings.json file is present:
        settings_json_file = os.environ['SAML_V2_METADATA_FOLDER']
        if not os.path.exists(settings_json_file):
            app.logger.info('SSO settings.json file not found, SSO will be disabled')
        else:
            app.logger.info('SSO settings.json file found')

    # Register own class encoder
    app.json_encoder = CustomJsonEncoder
except Exception as error:
    app.logger.error(
        f'The following error occurs when trying to load configuration file in located :{os.environ["SOS_TRADES_SERVER_CONFIGURATION"]}\n{error} ')
    raise error
    exit(-1)

# Register own class for studycase caching
study_case_cache = StudyCaseCache()

# Create authentication token (JWT) manager
jwt = JWTManager(app)

# Using the expired_token_loader decorator, we will now call
# this function whenever an expired but otherwise valid access
# token attempts to access an endpoint


def database_process_setup():
    from sos_trades_api.tools.process_management.process_management import update_database_with_process
    from sos_trades_api.tools.reference_management.reference_management import update_database_with_references
    from sos_trades_api.controllers.sostrades_main.study_case_controller import clean_database_with_disabled_study_case
    """ Launch process setup in database

    :return boolean (success or not)
    """
    database_initialized = False

    # Retrieve repository to check from configuration file
    additional_repository_list = app.config['SOS_TRADES_PROCESS_REPOSITORY']

    with app.app_context():
        try:
            # Retrieve administrator applicative account to set admin as
            # default user manager
            administrator_applicative_account = User.query.filter(
                User.username == User.APPLICATIVE_ACCOUNT_NAME).first()

            # Retrieve group from configuration to set admin as default
            # user manager
            group_manager_account_account = Group.query.filter(
                Group.name == app.config['DEFAULT_GROUP_MANAGER_ACCOUNT']).first()

            app.logger.info(
                'Starting loading available processes and references')
            update_database_with_process(additional_repository_list, app.logger,
                                         administrator_applicative_account, group_manager_account_account)
            update_database_with_references(app.logger)

            app.logger.info(
                'Finished loading available processes and references')
            app.logger.info('Clean disabled study case')
            clean_database_with_disabled_study_case(app.logger)
            app.logger.info('Finished cleaning disabled study case, server is ready...')

            database_initialized = True
        except:
            app.logger.exception(
                'An error occurs during database setup')

    return database_initialized


if app.config['ENVIRONMENT'] != UNIT_TEST:

    # Add custom command on flask cli to execute database setup
    # (mainly for manage gunicorn launch and avoid all worker to execute the command)
    @click.command('init_process')
    @with_appcontext
    def init_process():
        """ Execute process and reference database setup
        """
        database_process_setup()


    app.cli.add_command(init_process)

    @jwt.expired_token_loader
    def my_expired_token_callback(expired_token):
        return jsonify({
            'statusCode': 401,
            'name': 'Unauthorized',
            'description': 'User session expired, please log again'
        }), 401

    # override debug flag
    if '--debugger' in sys.argv:
        app.debug = True

    # Put here all imports from model
    # For migration to detect new tables
    # After running migration script, remove them from here to prevent import error
    if not app == None and not db == None:
        migrate = Migrate(app, db, compare_type=False)

    # Attention compare type find a difference in ReferenceGenerationStatus
    # if not app == None and not db == None:
    #     migrate = Migrate(app, db, compare_type=True)

    # load & register APIs
    # from sos_trades_api.routes import *


    # Register exception handler
    @app.errorhandler(Exception)
    def error_handler(error):
        """
        Standard Error Handler
        """
        app.logger.error(error)
        tb.print_exc()
        if isinstance(error, HTTPException):
            return jsonify({
                'statusCode': error.code,
                'name': error.name,
                'description': error.description
            }), error.code
        else:
            return jsonify({
                'statusCode': 500,
                'name': 'Internal Server Error',
                'description': str(error)
            }), 500
