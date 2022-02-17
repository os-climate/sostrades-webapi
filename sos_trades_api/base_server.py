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
    from sos_trades_api.models.database_models import User, Group, UserProfile
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
                Group.is_default_applicative_group).first()

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

def database_create_admin_user():
    '''
        Set initial data into db:
        create Administrator account and set password
        create test_user account and set password
        create default group ALL_users
    '''
    from sos_trades_api.controllers.sostrades_data.user_controller import create_administrator_account
    create_administrator_account()

def database_create_standard_user(username, email, firstname, lastname):
    '''
        Set initial data into db:
        create Administrator account and set password
        create test_user account and set password
        create default group ALL_users
    '''
    from sos_trades_api.controllers.sostrades_data.user_controller import create_standard_user_account
    create_standard_user_account(username, email, firstname, lastname)


def database_reset_admin_password():
    '''
        Reset Administrator password if account already exist
    '''
    database_reset_user_password(User.APPLICATIVE_ACCOUNT_NAME)


def database_reset_user_password(username):
    '''
        Reset user password if account already exist
        :param:username, username of the user
    '''
    from sos_trades_api.controllers.sostrades_data.user_controller import reset_user_password

    reset_user_password(username)

def database_rename_group(old_group_name, new_group_name):
    '''
        rename a group from old_group_name to new_group_name
    '''
    from sos_trades_api.controllers.sostrades_data.group_controller import rename_group

    rename_group(old_group_name, new_group_name)


if app.config['ENVIRONMENT'] != UNIT_TEST:

    # Add custom command on flask cli to execute database setup
    # (mainly for manage gunicorn launch and avoid all worker to execute the command)
    @click.command('init_process')
    @with_appcontext
    def init_process():
        """ Execute process and reference database setup
        """
        database_process_setup()

    # Add custom command on flask cli to execute database init data setup
    # (mainly for manage gunicorn launch and avoid all worker to execute the command)
    @click.command('create_admin_user')
    @with_appcontext
    def create_admin_user():
        """ admin and test user creation and default group creation database setup
        """
        database_create_admin_user()

    # Add custom command on flask cli to execute database init data setup
    # (mainly for manage gunicorn launch and avoid all worker to execute the command)
    @click.command('create_standard_user')
    @click.argument('username')
    @click.argument('email')
    @click.argument('firstname')
    @click.argument('lastname')
    @with_appcontext
    def create_standard_user(username, email, firstname, lastname):
        """ standard creation associated to ALl_user group
        :param:username, the identification name of the user, must be unique in users database
        :param:email, email of the user, must be unique in users database
        :param:firstname, first name of the user
        :param:lastname, last name of the user
        """
        database_create_standard_user(username, email, firstname, lastname)

    # Add custom command on flask cli to execute database init data setup
    # (mainly for manage gunicorn launch and avoid all worker to execute the command)
    @click.command('reset_admin_password')
    @with_appcontext
    def reset_admin_password():
        """ admin and test user creation and default group creation database setup
        """
        database_reset_admin_password()

    # Add custom command on flask cli to execute database init data setup
    # (mainly for manage gunicorn launch and avoid all worker to execute the command)
    @click.command('reset_standard_user_password')
    @click.argument('username')
    @with_appcontext
    def reset_standard_user_password(username):
        """ reset the password of a user with this username
        :param:username, the user name of the user
        """
        database_reset_user_password(username)

    # Add custom command on flask cli to execute database init data setup
    # (mainly for manage gunicorn launch and avoid all worker to execute the command)
    @click.command('rename_applicative_group')
    @click.argument('new_name')
    @with_appcontext
    def rename_applicative_group(new_name):
        """ rename a group from old_name to new_name
        """
        database_rename_group(Group.SOS_TRADES_DEV_GROUP, new_name)

    app.cli.add_command(init_process)
    app.cli.add_command(create_admin_user)
    app.cli.add_command(create_standard_user)
    app.cli.add_command(rename_applicative_group)
    app.cli.add_command(reset_admin_password)
    app.cli.add_command(reset_standard_user_password)

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
