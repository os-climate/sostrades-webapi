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
app.logger.propagate = False

for handler in app.logger.handlers:
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(name)s %(levelname)s in %(module)s: %(message)s"))


# Env constant
PRODUCTION = 'PRODUCTION'
ENVIRONMENT = 'ENVIRONMENT'
UNIT_TEST = 'UNIT_TEST'

try:
    config = Config()
    config.check()
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

    # Identity provider checks

    # -------- SAML V2 provider
    # Test if SAML settings file path is filled
    if os.environ.get('SAML_V2_METADATA_FOLDER') is None:
        app.logger.info('SAML_V2_METADATA_FOLDER configuration not found, SSO will be disabled')
    else:
        app.logger.info('SAML_V2_METADATA_FOLDER environment variable found')

        # Check that the settings.json file is present:
        sso_path = os.environ['SAML_V2_METADATA_FOLDER']
        if not os.path.exists(sso_path):
            app.logger.info('SSO folder not found, SSO will be disabled')
        else:
            app.logger.info('SSO folder file found')

    # -------- Github oauth provider
    if os.environ.get('GITHUB_OAUTH_SETTINGS') is None:
        app.logger.info('GITHUB_OAUTH_SETTINGS configuration not found, Github IdP/oauth will be disabled')
    else:
        app.logger.info('GITHUB_OAUTH_SETTINGS environment variable found')

        # Check that the settings.json file is present:
        settings_json_file = os.environ['GITHUB_OAUTH_SETTINGS']
        if not os.path.exists(settings_json_file):
            app.logger.info('GitHub IdP/oauth settings.json file not found, SSO will be disabled')
        else:
            app.logger.info('GitHub IdP/oauth settings.json file found')



    # Register own class encoder
    app.json_encoder = CustomJsonEncoder
except Exception as error:
    app.logger.error(
        f'The following error occurs when trying to initialize server\n{error} ')
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
            # Retrieve group from configuration to set admin as default
            # user manager
            group_manager_account_account = Group.query.filter(
                Group.is_default_applicative_group).first()
            if group_manager_account_account is None:
                group_manager_account_account = Group.query.filter(
                Group.name == Group.SOS_TRADES_DEV_GROUP).first()
                print('No default group have been found. Group Sostrades_dev is get by default')

            app.logger.info(
                'Starting loading available processes and references')
            update_database_with_process(additional_repository_list=additional_repository_list,
                                         logger=app.logger,
                                         default_manager_group=group_manager_account_account)
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


def database_create_standard_user(username, email, firstname, lastname):
    '''
        Set initial data into db:
        create Administrator account and set password
        create test_user account and set password
        create default group ALL_users
    '''
    from sos_trades_api.controllers.sostrades_data.user_controller import create_standard_user_account
    create_standard_user_account(username, email, firstname, lastname)


def database_reset_user_password(username):
    '''
        Reset user password if account already exist
        :param:username, username of the user
    '''
    from sos_trades_api.controllers.sostrades_data.user_controller import reset_local_user_password_by_name

    reset_local_user_password_by_name(username)


def database_rename_applicative_group(new_group_name):
    '''
        rename a group from old_group_name to new_group_name
    '''
    from sos_trades_api.controllers.sostrades_data.group_controller import rename_applicative_group

    rename_applicative_group(new_group_name)


def database_change_user_profile(username, new_profile=None):
    """
        Update a user profile
    :param username: user identifier
    :param new_profile: profile name to set (if not set then remove user profile)
    """
    from sos_trades_api.models.database_models import User, UserProfile

    with app.app_context():
        try:
            # Retrieve user account
            user = User.query.filter(User.username == username).first()

            if user is None:
                raise Exception(f'User {username} not found')

            # Get old user profile for logging purpose"
            old_user_profile = UserProfile.query.filter(UserProfile.id == user.user_profile_id).first()
            old_user_profile_name = None
            if old_user_profile is not None:
                old_user_profile_name = old_user_profile.name

            # Get information's about new profile
            new_profile_id = None
            if new_profile is not None:
                new_user_profile = UserProfile.query.filter(UserProfile.name == new_profile).first()
                if new_user_profile is None:
                    raise Exception(f'Profile {new_profile} not found')
                else:
                    new_profile_id = new_user_profile.id

            # Update the user if changed is required
            if not user.user_profile_id == new_profile_id:
                user.user_profile_id = new_profile_id
                db.session.add(user)
                db.session.commit()
                app.logger.info(f'User {username} profile changed from {old_user_profile_name} to {new_profile}')
            else:
                app.logger.info(f'Profile already up-to-date')

        except:
            app.logger.exception(
                'An error occurs during database setup')


def database_create_api_key(group_name, api_key_name):
    """
    Create a new api key for the given group in database
    :param group_name: Group identifier to assign api key
    :type group_name: str
    :param api_key_name: Name to set to the api key
    :type api_key_name: str
    """

    from sos_trades_api.models.database_models import Group, Device, GroupAccessUser, AccessRights

    with app.app_context():
        # First check that group has an owner
        result = db.session.query(User, Group, GroupAccessUser, AccessRights) \
            .filter(User.id == GroupAccessUser.user_id) \
            .filter(Group.id == GroupAccessUser.group_id) \
            .filter(Group.name == group_name) \
            .filter(GroupAccessUser.right_id == AccessRights.id) \
            .filter(AccessRights.access_right == AccessRights.OWNER).first()

        if result is None:
            app.logger.error('To generate an api key, the group must exist and have a user as group OWNER.')
            exit()

        group = result.Group

        device_already_exist = Device.query.filter(Device.group_id == group.id).first()

        if device_already_exist:
            app.logger.error('There is already an api key available for this group')
            exit()

        device = Device()
        device.device_name = api_key_name
        device.group_id = group.id

        db.session.add(device)
        db.session.commit()

        app.logger.info('The following api key has been created')
        app.logger.info(device)


def database_renew_api_key(group_name):
    """
    Renew api key for the given group in database
    :param group_name: Group identifier with assigned api key
    :type group_name: str
    """

    from sos_trades_api.models.database_models import Group, Device

    with app.app_context():
        # First check that group has an owner
        result = db.session.query(Group, Device) \
            .filter(Group.id == Device.group_id) \
            .filter(Group.name == group_name).first()

        if result is None:
            app.logger.error('No api key found for this group')
            exit()

        device = result.Device

        # Update key value
        temp_device = Device()
        device.device_key = temp_device.device_key

        db.session.add(device)
        db.session.commit()

        app.logger.info('The following api key has been updated')
        app.logger.info(device)


def database_revoke_api_key(group_name):
    """
    Revoke api key for the given group in database
    :param group_name: Group identifier with assigned api key
    :type group_name: str
    """

    from sos_trades_api.models.database_models import Group, Device

    with app.app_context():
        # First check that group has an owner
        result = db.session.query(Group, Device) \
            .filter(Group.id == Device.group_id) \
            .filter(Group.name == group_name).first()

        if result is None:
            app.logger.error('No api key found for this group.')
            exit()

        device = result.Device

        db.session.delete(device)
        db.session.commit()

        app.logger.info('The following api key has been deleted')
        app.logger.info(device)


def database_list_api_key():
    """
    list all database api key
    """

    from sos_trades_api.models.database_models import Device

    with app.app_context():
        # First check that group has an owner
        devices = Device.query.all()

        if len(devices) == 0:
            app.logger.info('No api key found')
        else:
            app.logger.info('Existing api key list')
            for device in devices:
                app.logger.info(device)


if app.config['ENVIRONMENT'] != UNIT_TEST:

    # Add custom command on flask cli to execute database setup
    # (mainly for manage gunicorn launch and avoid all worker to execute the command)
    @click.command('init_process')
    @click.option('-d', '--debug', is_flag=True)
    @with_appcontext
    def init_process(debug):
        """
        Execute process and reference database setup

        :param debug: show DEBIG log
        :type debug: boolean
        """

        if debug:
            app.logger.setLevel(logging.DEBUG)
        else:
            app.logger.setLevel(logging.INFO)
        database_process_setup()

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
        database_rename_applicative_group(new_name)


    @click.command('change_user_profile')
    @click.argument('username')
    @click.option('-p', '--profile', type=click.Choice([UserProfile.STUDY_MANAGER, UserProfile.STUDY_USER]), default=None)
    @with_appcontext
    def change_user_profile(username, profile):
        """ update user profile
        :param:username, the identification name of the user
        :param:profile, profile value , 'Study user', 'Study manager' or nothing to set no profile
        """

        app.logger.setLevel(0)
        if profile is None or len(profile) == 0:
            profile = None
        database_change_user_profile(username, profile)


    @click.command('create_api_key')
    @click.argument('group_name')
    @click.argument('api_key_name')
    @with_appcontext
    def create_api_key(group_name, api_key_name):
        """ create an api key
        :param group_name: the group name to assign api key
        :type group_name: str
        :param api_key_name: name to set to the api key
        :type group_name: str
        """

        database_create_api_key(group_name, api_key_name)


    @click.command('renew_api_key')
    @click.argument('group_name')
    @with_appcontext
    def renew_api_key(group_name):
        """ update an api key
        :param group_name: the group name to renew api key
        :type group_name: str
        """

        database_renew_api_key(group_name)


    @click.command('revoke_api_key')
    @click.argument('group_name')
    @with_appcontext
    def revoke_api_key(group_name):
        """ revoke an api key
        :param: group_name, the group name to revoke api key
        :type group_name: str
        """

        database_revoke_api_key(group_name)


    @click.command('list_api_key')
    @with_appcontext
    def list_api_key():
        """ List all database api key
        """

        database_list_api_key()

    app.cli.add_command(init_process)
    app.cli.add_command(create_standard_user)
    app.cli.add_command(rename_applicative_group)
    app.cli.add_command(reset_standard_user_password)
    app.cli.add_command(change_user_profile)
    app.cli.add_command(create_api_key)
    app.cli.add_command(renew_api_key)
    app.cli.add_command(revoke_api_key)
    app.cli.add_command(list_api_key)

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


if __name__ == "main":
    database_process_setup()