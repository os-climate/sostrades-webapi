'''
Copyright 2022 Airbus SAS
Modifications on 2023/11/22-2024/06/25 Copyright 2023 Capgemini

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
import logging
import os
import re
import sys
import time
import traceback as tb
from datetime import datetime
from os.path import join

import click
from flask import Flask, jsonify, make_response, request, session
from flask.cli import with_appcontext
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from werkzeug.exceptions import HTTPException

from sos_trades_api.config import Config

START_TIME = "start_time"
first_line_time = time.time()

# Create  flask server and set local configuration
server_name = __name__
if os.environ.get("SERVER_NAME") is not None:
    server_name = os.environ["SERVER_NAME"]

app = Flask(server_name)

app.logger.propagate = False

for handler in app.logger.handlers:
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(name)s %(levelname)s in %(module)s: %(message)s"))


# Env constant
PRODUCTION = "PRODUCTION"
ENVIRONMENT = "ENVIRONMENT"
UNIT_TEST = "UNIT_TEST"

try:
    app.logger.info("Loading configuration")
    config = Config()
    config.check()
    flask_config_dict = config.get_flask_config_dict()
    app.config.update(flask_config_dict)

    app.logger.info("Connecting to database")
    # Register database on app
    db = SQLAlchemy()
    db.init_app(app)

    # As flask application and database are initialized, then import
    # sos_trades_api dependencies

    app.logger.info("Importing dependencies")
    from sos_trades_api.models.custom_json_encoder import CustomJsonProvider
    from sos_trades_api.models.database_models import Group, User, UserProfile
    from sos_trades_api.tools.cache.study_case_cache import StudyCaseCache
    from sos_trades_api.tools.logger.application_mysql_handler import (
        ApplicationMySQLHandler,
        ApplicationRequestFormatter,
    )

    app.logger.info("Adding application logger handler")
    app_mysql_handler = ApplicationMySQLHandler(
        db=config.logging_database_data)
    app_mysql_handler.setFormatter(ApplicationRequestFormatter(
        "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"))
    app.logger.addHandler(app_mysql_handler)

    app.logger.info("Configuring logger")
    if app.config["ENVIRONMENT"] == PRODUCTION:
        logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [worker: %(process)d] %(name)s %(levelname)s in %(module)s: %(message)s")

        # Remove all trace
        logging.getLogger("engineio.server").setLevel(51)
    else:
        logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [worker: %(process)d] %(name)s %(levelname)s in %(module)s: %(message)s")
        app.logger.setLevel(logging.DEBUG)
        logging.getLogger("engineio.server").setLevel(logging.DEBUG)

    for handler in logging.getLogger().handlers:
        handler.setFormatter(logging.Formatter("[%(asctime)s] [worker: %(process)d] %(name)s %(levelname)s in %(module)s: %(message)s"))
    app.logger.info(f'{app.config["ENVIRONMENT"]} environment configuration loaded')
    app.logger.info(f"Time elapsed since python beginning: {(time.time() - first_line_time):.2f} seconds")

    # Register own class encoder
    app.json_provider_class = CustomJsonProvider
    app.json = CustomJsonProvider(app)
except Exception as error:
    app.logger.error(
        f"The following error occurs when trying to initialize server\n{error} ")
    raise error
    exit(-1)

# Register own class for studycase caching
study_case_cache = StudyCaseCache(logger=app.logger)

# Create authentication token (JWT) manager
jwt = JWTManager(app)




def get_study_id_for_study_server():
    '''
    If the pod is a study server, find the study ID:
    The study server has a HOSTNAME named sostrades-study-server-[study_id]
    :return: study id (int) (None if the study server is not )
    '''
    study_id = None
    pod_name =os.environ.get("HOSTNAME", "")
    if pod_name.startswith("sostrades-study-server-"):
        #retreive study id
        match = re.search(r"(?<=sostrades-study-server-)\d+", pod_name)
        if match:
            #the number represents the study id
            study_id = int(match.group(0))
        else:
            exception_message = f"Could not find the study ID in the pod environment variable HOSTNAME={pod_name}"
            app.logger.exception(exception_message)
            raise Exception(exception_message)
    return study_id


def load_specific_study(study_identifier):
    """
    Load a specific study.
    Generally used when a specific study is launched to manage an unique study at startup
    :param study_identifier: database identifier of the study to load
    :type study_identifier: integer

    """
    from sos_trades_api.controllers.sostrades_main.study_case_controller import (
        load_or_create_study_case,
    )

    with app.app_context():
        load_or_create_study_case(study_identifier)
        

# in case of study server, find the study server ID
study_id = get_study_id_for_study_server()
if study_id is not None:
    # in case of study server, save the active study file and load the study
    from sos_trades_api.tools.active_study_management.active_study_management import (
        ACTIVE_STUDY_FILE_NAME,
        save_study_last_active_date,
    )
    # create the active study file if it doesn't exist
    local_path = Config().local_folder_path
    if local_path != "" and os.path.exists(local_path):
        file_path = os.path.join(local_path, f"{ACTIVE_STUDY_FILE_NAME}{study_id}.txt")
        if not os.path.exists(file_path):
            save_study_last_active_date(study_id, datetime.now())
    
    # then load the study
    load_specific_study(study_id)

def database_process_setup():
    from sos_trades_api.controllers.sostrades_main.study_case_controller import (
        clean_database_with_disabled_study_case,
    )
    from sos_trades_api.tools.allocation_management.allocation_management import (
        clean_all_allocations_type_reference,
    )
    from sos_trades_api.tools.process_management.process_management import (
        update_database_with_process,
    )
    from sos_trades_api.tools.reference_management.reference_management import (
        update_database_with_references,
    )
    """ Launch process setup in database

    :return boolean (success or not)
    """
    database_initialized = False

    # Retrieve repository to check from configuration file
    additional_repository_list = app.config["SOS_TRADES_PROCESS_REPOSITORY"]

    with app.app_context():
        try:
            # Retrieve group from configuration to set admin as default
            # user manager
            group_manager_account_account = Group.query.filter(
                Group.is_default_applicative_group).first()
            if group_manager_account_account is None:
                group_manager_account_account = Group.query.filter(
                    Group.name == Group.SOS_TRADES_DEV_GROUP).first()
                print(
                    "No default group have been found. Group Sostrades_dev is get by default")

            app.logger.info(
                "Starting loading available processes and references")
            update_database_with_process(additional_repository_list=additional_repository_list,
                                         logger=app.logger,
                                         default_manager_group=group_manager_account_account)
            update_database_with_references(app.logger)

            app.logger.info(
                "Finished loading available processes and references")

            app.logger.info("Clean reference pod allocations")
            clean_all_allocations_type_reference(app.logger)
            app.logger.info("Finished cleaning pod allocation references")

            app.logger.info("Clean disabled study case")
            clean_database_with_disabled_study_case(app.logger)
            app.logger.info(
                "Finished cleaning disabled study case, server is ready...")

            database_initialized = True
        except:
            app.logger.exception(
                "An error occurs during database setup")

    return database_initialized


def check_identity_provider_availability():
    """
    Check is environment variable needed to activate SAML_V2 compatible identity provider or
    GitHub OAuth provider are available.
    """
    # -------- SAML V2 provider
    # Test if SAML settings file path is filled
    if os.environ.get("SAML_V2_METADATA_FOLDER") is None:
        app.logger.info(
            "SAML_V2_METADATA_FOLDER configuration not found, SSO will be disabled")
    else:
        app.logger.info("SAML_V2_METADATA_FOLDER environment variable found")

        # Check that the settings.json file is present:
        sso_path = os.environ["SAML_V2_METADATA_FOLDER"]
        if not os.path.exists(sso_path):
            app.logger.info("SSO folder not found, SSO will be disabled")
        else:
            app.logger.info("SSO folder file found")

    # -------- Github oauth provider
    if os.environ.get("GITHUB_OAUTH_SETTINGS") is None:
        app.logger.info(
            "GITHUB_OAUTH_SETTINGS configuration not found, Github IdP/oauth will be disabled")
    else:
        app.logger.info("GITHUB_OAUTH_SETTINGS environment variable found")

        # Check that the settings.json file is present:
        settings_json_file = os.environ["GITHUB_OAUTH_SETTINGS"]
        if not os.path.exists(settings_json_file):
            app.logger.info(
                "GitHub IdP/oauth settings.json file not found, SSO will be disabled")
        else:
            app.logger.info("GitHub IdP/oauth settings.json file found")


def database_check_study_case_state(with_deletion=False):
    """
    Check study case state in database

    Try to load each of them and store loading status and last modification date
    Give as outputs all study case that cannot be loaded and have more than one month
    with no changes.

    :param with_deletion: delete every failed or unreferenced study
    :type with_deletion: boolean
    """
    from datetime import datetime, timezone
    from os import listdir, path
    from shutil import rmtree

    from urllib3 import disable_warnings
    from urllib3.exceptions import InsecureRequestWarning

    from sos_trades_api.controllers.sostrades_main.study_case_controller import (
        delete_study_cases,
    )
    from sos_trades_api.models.database_models import Group, StudyCase
    from sos_trades_api.tools.loading.study_case_manager import StudyCaseManager

    studies_to_delete = []
    folders_to_delete = []

    disable_warnings(InsecureRequestWarning)

    # Remove INFO/WARNING level to avoid pushing too many log
    logging.disable(logging.INFO)
    logging.disable(logging.WARNING)
    print("Only Error, Fatal and Critical logging message will be displayed.")

    study_on_disk = {}

    with app.app_context():

        all_study_case = StudyCase.query.all()
        all_group = Group.query.all()

        print("\nCheck file system regarding available data's")
        base_path = StudyCaseManager.get_root_study_data_folder()

        # Get all sub elements inside root data folder (looking for group
        # folder)
        group_folder_list = listdir(base_path)
        for group_folder in group_folder_list:

            # Construct the path to the current element and check the element
            # is a folder
            built_group_path = join(base_path, group_folder)
            if path.isdir(built_group_path) and group_folder.isdigit():

                # Get all sub elements inside group data folder (looking for
                # study folder)
                study_folder_list = listdir(built_group_path)

                for study_folder in study_folder_list:
                    # Construct the path to the current element and check the
                    # element is a folder
                    built_study_path = join(built_group_path, study_folder)

                    if path.isdir(built_study_path) and study_folder.isdigit():
                        study_on_disk[int(study_folder)] = int(group_folder)

        print(f"\n{len(all_study_case)} study case(s) to check.\n")

        study_loaded_synthesis = []
        # Try to load each of them
        for study_case in all_study_case:
            is_load_ok = False
            is_date_ok = False
            try:
                study_case_manager = StudyCaseManager(study_case.id)
                study_case_manager.load_study_case_from_source()
                is_load_ok = True

                current_date = datetime.now().astimezone(timezone.utc).replace(tzinfo=None)
                date_delta = current_date - study_case.modification_date
                print(
                    f"DATE CHECK : {current_date} - {study_case.modification_date} - {date_delta.days}")
                is_date_ok = date_delta.days > 30

            except:
                is_load_ok = False

            # Remove study from study_on_disk dictionary
            if study_case.id in study_on_disk and study_on_disk[study_case.id] == study_case.group_id:
                del study_on_disk[study_case.id]

            study_group_result = list(
                filter(lambda g: g.id == study_case.group_id, all_group))
            group_name = "Unknown"
            if len(study_group_result) == 1:
                group_name = study_group_result[0].name

            if is_load_ok:
                message = f"{study_case.id:<5} | {study_case.name:<30} | {study_case.repository:<70} | {study_case.process:<35} | {study_case.modification_date} | {group_name:<15} | SUCCESS"
            elif is_date_ok:
                message = f"{study_case.id:<5} | {study_case.name:<30} | {study_case.repository:<70} | {study_case.process:<35} | {study_case.modification_date} | {group_name:<15} | PARTIAL"
            else:
                message = f"{study_case.id:<5} | {study_case.name:<30} | {study_case.repository:<70} | {study_case.process:<35} | {study_case.modification_date} | {group_name:<15} | FAILED"
                if with_deletion:
                    studies_to_delete.append(study_case.id)
            study_loaded_synthesis.append(message)

        print("\n".join(study_loaded_synthesis))

        if with_deletion and len(studies_to_delete) > 0:
            delete_study_cases(studies_to_delete)
            print(f"All failed database studies deleted {studies_to_delete}.")

        for study_folder, group_folder in study_on_disk.items():
            study_group_result = list(
                filter(lambda g: g.id == int(group_folder), all_group))
            group_name = "Unknown"
            if len(study_group_result) == 1:
                group_name = f"{study_group_result[0].name}?"
            print(
                f'{study_folder:<5} | {" ":<30} | {" ":<70} | {" ":<35} | {" ":<19} | {group_name:<15} | UNREFERENCED')

            if with_deletion:
                folder = join(base_path, f"{group_folder}", f"{study_folder}")
                folders_to_delete.append(folder)

        if with_deletion and len(folders_to_delete) > 0:
            for folder in folders_to_delete:
                rmtree(folder, ignore_errors=True)
                print(f"Folder {folder:<128} deleted.")


def database_create_standard_user(username, email, firstname, lastname):
    """
    Set initial data into db:
    create Administrator account and set password
    create test_user account and set password
    create default group ALL_users
    """
    from sos_trades_api.controllers.sostrades_data.user_controller import (
        create_standard_user_account,
    )
    create_standard_user_account(username, email, firstname, lastname)


def database_reset_user_password(username):
    """
    Reset user password if account already exist

    :param:username, username of the user
    """
    from sos_trades_api.controllers.sostrades_data.user_controller import (
        reset_local_user_password_by_name,
    )

    reset_local_user_password_by_name(username)


def database_rename_applicative_group(new_group_name):
    """
    Rename a group from old_group_name to new_group_name
    """
    from sos_trades_api.controllers.sostrades_data.group_controller import (
        rename_applicative_group,
    )

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
                raise Exception(f"User {username} not found")

            # Get old user profile for logging purpose"
            old_user_profile = UserProfile.query.filter(
                UserProfile.id == user.user_profile_id).first()
            old_user_profile_name = None
            if old_user_profile is not None:
                old_user_profile_name = old_user_profile.name

            # Get information's about new profile
            new_profile_id = None
            if new_profile is not None:
                new_user_profile = UserProfile.query.filter(
                    UserProfile.name == new_profile).first()
                if new_user_profile is None:
                    raise Exception(f"Profile {new_profile} not found")
                else:
                    new_profile_id = new_user_profile.id

            # Update the user if changed is required
            if user.user_profile_id != new_profile_id:
                user.user_profile_id = new_profile_id
                db.session.add(user)
                db.session.commit()
                app.logger.info(
                    f"User {username} profile changed from {old_user_profile_name} to {new_profile}")
            else:
                app.logger.info("Profile already up-to-date")

        except:
            app.logger.exception(
                "An error occurs during database setup")


def database_create_api_key(group_name, api_key_name):
    """
    Create a new api key for the given group in database

    :param group_name: Group identifier to assign api key
    :type group_name: str

    :param api_key_name: Name to set to the api key
    :type api_key_name: str
    """
    from sos_trades_api.models.database_models import (
        AccessRights,
        Device,
        Group,
        GroupAccessUser,
    )

    with app.app_context():
        # First check that group has an owner
        result = db.session.query(User, Group, GroupAccessUser, AccessRights) \
            .filter(User.id == GroupAccessUser.user_id) \
            .filter(Group.id == GroupAccessUser.group_id) \
            .filter(Group.name == group_name) \
            .filter(GroupAccessUser.right_id == AccessRights.id) \
            .filter(AccessRights.access_right == AccessRights.OWNER).first()

        if result is None:
            app.logger.error(
                "To generate an api key, the group must exist and have a user as group OWNER.")
            exit()

        group = result.Group

        device_already_exist = Device.query.filter(
            Device.group_id == group.id).first()

        if device_already_exist:
            app.logger.error(
                "There is already an api key available for this group")
            exit()

        device = Device()
        device.device_name = api_key_name
        device.group_id = group.id

        db.session.add(device)
        db.session.commit()

        app.logger.info("The following api key has been created")
        app.logger.info(device)


def database_renew_api_key(group_name):
    """
    Renew api key for the given group in database

    :param group_name: Group identifier with assigned api key
    :type group_name: str
    """
    from sos_trades_api.models.database_models import Device, Group

    with app.app_context():
        # First check that group has an owner
        result = db.session.query(Group, Device) \
            .filter(Group.id == Device.group_id) \
            .filter(Group.name == group_name).first()

        if result is None:
            app.logger.error("No api key found for this group")
            exit()

        device = result.Device

        # Update key value
        temp_device = Device()
        device.device_key = temp_device.device_key

        db.session.add(device)
        db.session.commit()

        app.logger.info("The following api key has been updated")
        app.logger.info(device)


def database_revoke_api_key(group_name):
    """
    Revoke api key for the given group in database

    :param group_name: Group identifier with assigned api key
    :type group_name: str
    """
    from sos_trades_api.models.database_models import Device, Group

    with app.app_context():
        # First check that group has an owner
        result = db.session.query(Group, Device) \
            .filter(Group.id == Device.group_id) \
            .filter(Group.name == group_name).first()

        if result is None:
            app.logger.error("No api key found for this group.")
            exit()

        device = result.Device

        db.session.delete(device)
        db.session.commit()

        app.logger.info("The following api key has been deleted")
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
            app.logger.info("No api key found")
        else:
            app.logger.info("Existing api key list")
            for device in devices:
                app.logger.info(device)


def clean_all_allocations_method():
    from sos_trades_api.tools.allocation_management.allocation_management import (
        clean_all_allocations_type_study,
    )
    clean_all_allocations_type_study()

def clean_inactive_study_pods():
    from sos_trades_api.controllers.sostrades_main.study_case_controller import (
        check_study_is_still_active_or_kill_pod,
    )

    check_study_is_still_active_or_kill_pod()

def update_all_pod_status_method():
    from sos_trades_api.tools.allocation_management.allocation_management import (
        update_all_pod_status,
    )
    update_all_pod_status()

def update_all_pod_status_loop_method():
    from sos_trades_api.tools.allocation_management.allocation_management import (
        update_all_pod_status,
    )
    interval = 15 #seconds
    while True:
        try:
            update_all_pod_status()
            app.logger.info("Retrieved status of pod of kubernetes from launch_thread_update_pod_allocation_status()")
        except Exception as ex:
            app.logger.exception("Exception while updating pod allocation status", exc_info=ex)
        if not Config().pod_watcher_activated:
            time.sleep(interval)

if app.config["ENVIRONMENT"] != UNIT_TEST:

    # Add custom command on flask cli to execute database setup
    # (mainly for manage gunicorn launch and avoid all worker to execute the command)
    @click.command("init_process")
    @click.option("-d", "--debug", is_flag=True)
    @with_appcontext
    def init_process(debug):
        """
        Execute process and reference database setup

        :param debug: show DEBUG log
        :type debug: boolean
        """
        if debug:
            app.logger.setLevel(logging.DEBUG)
        else:
            app.logger.setLevel(logging.INFO)
        database_process_setup()

    @click.command("check_study_case_state")
    @click.option("-wd", "--with_deletion", is_flag=True)
    @with_appcontext
    def check_study_case_state(with_deletion):
        """
        Check study case state in database
        Try to load each of them and store loading status and last modification date
        Give as outputs all study case that cannot be loaded and have more than one month
        with no changes.

        :param with_deletion: delete every failed or unreferenced study
        :type with_deletion: boolean
        """
        database_check_study_case_state(with_deletion)

    # Add custom command on flask cli to execute database init data setup
    # (mainly for manage gunicorn launch and avoid all worker to execute the command)
    @click.command("create_standard_user")
    @click.argument("username")
    @click.argument("email")
    @click.argument("firstname")
    @click.argument("lastname")
    @with_appcontext
    def create_standard_user(username, email, firstname, lastname):
        """
        standard creation associated to ALl_user group
        :param:username, the identification name of the user, must be unique in users database
        :param:email, email of the user, must be unique in users database
        :param:firstname, first name of the user
        :param:lastname, last name of the user
        """
        database_create_standard_user(username, email, firstname, lastname)

    # Add custom command on flask cli to execute database init data setup
    # (mainly for manage gunicorn launch and avoid all worker to execute the command)
    @click.command("reset_standard_user_password")
    @click.argument("username")
    @with_appcontext
    def reset_standard_user_password(username):
        """
        reset the password of a user with this username
        :param:username, the user name of the user
        """
        database_reset_user_password(username)


    # Add custom command on flask cli to execute database init data setup
    # (mainly for manage gunicorn launch and avoid all worker to execute the command)
    @click.command("create_user_test")
    @click.argument("username")
    @click.argument("password")
    @with_appcontext
    def create_user_test(username, password):
        """
        user_test creation
        :param:username, the identification name of the user, must be unique in users database
        :param:password, password of the user count
        :param:profile, the user profile
        """
        from sos_trades_api.controllers.sostrades_data.user_controller import (
            database_create_user_test,
        )
        # Create the user test
        try:
            database_create_user_test(username, password)
            app.logger.info(f"{username} has been successfully created")
        except Exception as ex:
            app.logger.error(f"The following error occurs when trying to create user_test\n{ex} ")
            raise ex

    # Add custom command on flask cli to execute database init data setup
    @click.command("set_user_access_group")
    @click.argument("username")
    @click.argument("group_list_str")
    @with_appcontext
    def set_user_access_group(username, group_list_str):
        """
        Give user rights at groups
        :param:username, the identification name of the user, must be unique in users database
        :param:group_list_str, the list of group targeted
        """
        from sos_trades_api.controllers.sostrades_data.user_controller import (
            database_set_user_access_group,
        )

        # Transform the string to a list
        group_list = group_list_str.split(",")
        group_list = [group.strip() for group in group_list]
        try:
            database_set_user_access_group(group_list, username)
            app.logger.info(f'The group_access_user for "{group_list_str}" has been successfully updated to "{username}"')

        except Exception as ex:
            app.logger.error(f"The following error occurs when trying to set access right to a group\n{ex}")
            raise ex

    # Add custom command on flask cli to execute database init data setup
    # (mainly for manage gunicorn launch and avoid all worker to execute the command)
    @click.command("set_process_access_user")
    @click.argument("username")
    @click.argument("process_list_str")
    @with_appcontext
    def set_process_access_user(username, process_list_str):
        """
        Set the necessary processes access at the user
        :param:username, the identification name of the user, must be unique in users database
        :param:process_list, the list of process targeted
        """
        from sos_trades_api.tools.process_management.process_management import (
            set_processes_to_user,
        )

        # Transform the string to a list
        process_list = process_list_str.split(",")
        process_list = [process.strip() for process in process_list]

        try:
            # retrieve the created user_test
            user = User.query.filter(User.username == username).first()
            if user is not None:
                set_processes_to_user(process_list, user.id, app.logger)
                app.logger.info(
                    f'The process_access_user for "{process_list_str}" has been successfully updated to "{username}"')

            else:
                raise Exception(f"User {username} not found in database")
        except Exception as ex:
            app.logger.error(f"The following error occurs when trying to set process to test user\n{ex} ")
            raise ex

    # Add custom command on flask cli to execute database init data setup
    # (mainly for manage gunicorn launch and avoid all worker to execute the command)
    @click.command("rename_applicative_group")
    @click.argument("new_name")
    @with_appcontext
    def rename_applicative_group(new_name):
        """
        rename a group from old_name to new_name
        """
        database_rename_applicative_group(new_name)

    @click.command("change_user_profile")
    @click.argument("username")
    @click.option("-p", "--profile", type=click.Choice([UserProfile.STUDY_MANAGER, UserProfile.STUDY_USER, UserProfile.STUDY_USER_NO_EXECUTION]), default=None)
    @with_appcontext
    def change_user_profile(username, profile):
        """
        update user profile
        :param:username, the identification name of the user
        :param:profile, profile value , 'Study user', 'Study manager', 'Study user without execution', or nothing to set no profile
        """
        app.logger.setLevel(0)
        if profile is None or len(profile) == 0:
            profile = None
        database_change_user_profile(username, profile)

    @click.command("create_api_key")
    @click.argument("group_name")
    @click.argument("api_key_name")
    @with_appcontext
    def create_api_key(group_name, api_key_name):
        """
        create an api key
        :param group_name: the group name to assign api key
        :type group_name: str
        :param api_key_name: name to set to the api key
        :type group_name: str
        """
        database_create_api_key(group_name, api_key_name)

    @click.command("renew_api_key")
    @click.argument("group_name")
    @with_appcontext
    def renew_api_key(group_name):
        """
        update an api key
        :param group_name: the group name to renew api key
        :type group_name: str
        """
        database_renew_api_key(group_name)

    @click.command("revoke_api_key")
    @click.argument("group_name")
    @with_appcontext
    def revoke_api_key(group_name):
        """
        revoke an api key
        :param: group_name, the group name to revoke api key
        :type group_name: str
        """
        database_revoke_api_key(group_name)

    @click.command("list_api_key")
    @with_appcontext
    def list_api_key():
        """
        List all database api key
        """
        database_list_api_key()

    # Add custom command on flask cli to clean allocations, services and
    # deployments
    @click.command("clean_all_allocations")
    @with_appcontext
    def clean_all_allocations():
        """
        delete all allocations from db and delete services and deployments with kubernetes api
        """
        clean_all_allocations_method()

    # Add custom command on flask cli to clean inactive allocation, service and
    # deployment
    @click.command("clean_inactive_study_pod")
    @with_appcontext
    def clean_inactive_study_pod():
        """
        delete inactive current study allocation from db and delete service and deployment with kubernetes api
        """
        clean_inactive_study_pods()

    # Add custom command on flask cli to update all current allocations
    @click.command("update_pod_allocations_status")
    @with_appcontext
    def update_pod_allocations_status():
        """
        update all allocations from db
        """
        update_all_pod_status_method()

    # Add custom command on flask cli to update all current allocations
    @click.command("update_pod_allocations_status_loop")
    @with_appcontext
    def update_pod_allocations_status_loop():
        """
        update all allocations from db
        """
        update_all_pod_status_loop_method()

    app.cli.add_command(init_process)
    app.cli.add_command(check_study_case_state)
    app.cli.add_command(create_standard_user)
    app.cli.add_command(rename_applicative_group)
    app.cli.add_command(reset_standard_user_password)
    app.cli.add_command(change_user_profile)
    app.cli.add_command(create_api_key)
    app.cli.add_command(renew_api_key)
    app.cli.add_command(revoke_api_key)
    app.cli.add_command(list_api_key)
    app.cli.add_command(clean_all_allocations)
    app.cli.add_command(clean_inactive_study_pod)
    app.cli.add_command(create_user_test)
    app.cli.add_command(set_user_access_group)
    app.cli.add_command(set_process_access_user)
    app.cli.add_command(update_pod_allocations_status)
    app.cli.add_command(update_pod_allocations_status_loop)

    # Using the expired_token_loader decorator, we will now call
    # this function whenever an expired but otherwise valid access
    # token attempts to access an endpoint

    @jwt.expired_token_loader
    def my_expired_token_callback(jwt_header, jwt_data):
        return jsonify({
            "statusCode": 401,
            "name": "Unauthorized",
            "description": "User session expired, please log again",
        }), 401

    # override debug flag
    if "--debugger" in sys.argv:
        app.debug = True

    # Put here all imports from model
    # For migration to detect new tables
    # After running migration script, remove them from here to prevent import
    # error
    if app is not None and db is not None:
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
                "statusCode": error.code,
                "name": error.name,
                "description": error.description,
            }), error.code
        else:
            return jsonify({
                "statusCode": 500,
                "name": "Internal Server Error",
                "description": str(error),
            }), 500

    @app.before_request
    def before_request():
        session[START_TIME] = time.time()

    @app.after_request
    def after_request(response):

        # Set logging info regarding request processing time
        duration = 0
        if START_TIME in session:
            duration = time.time() - session[START_TIME]

        app.logger.info(
            f"{request.remote_addr}, {request.method}, {request.scheme}, {request.full_path}, {response.status}, {duration} sec.",
        )

        # Enable CORS requests for local development
        # The following will allow the local angular-cli development environment to
        # make requests to this server (otherwise, you will get 403s due to same-
        # origin poly)
        response.headers.add("Access-Control-Allow-Origin",
                             "http://localhost:4200")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        response.headers.add("Access-Control-Allow-Headers",
                             'Content-Type,Authorization,Set-Cookie,Cookie,Cache-Control,Pragma,Expires')
        response.headers.add("Access-Control-Allow-Methods",
                             "GET,PUT,POST,DELETE")

        # disable caching all requests
        response.cache_control.no_cache = True
        response.cache_control.no_store = True
        response.cache_control.must_revalidate = True

        return response


@app.route("/api/ping", methods=["GET"])
def ping():
    return make_response(jsonify("pong"), 200)
