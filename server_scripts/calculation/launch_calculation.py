'''
Copyright 2022 Airbus SAS
Modifications on 2023/05/12-2023/11/03 Copyright 2023 Capgemini

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
# coding: utf-8
import os
import time
import argparse
import logging
import yaml
import git
import re
from os import environ, pathsep
from os.path import join, dirname, isdir
from datetime import datetime, timezone
from dotenv import load_dotenv
from logging import DEBUG

BRANCH = 'branch'
COMMIT = 'commit'
URL = 'url'
COMMITTED_DATE = 'committed_date'
REPO_PATH = 'path'

# Regular expression to remove connection info from url when token is used
INFO_REGEXP = ':\/\/.*@'
INFO_REPLACE = '://'


class ReferenceStudyError(Exception):
    """
    Exception class to manage reference study error
    """


def launch_calculation_study(study_identifier):
    """
    Calculate study given as identifier
    :param study_identifier: study to calculate
    """

    # Initialize execution logger
    execution_logger = logging.getLogger(__name__)

    study_case = None
    exec_engine = None

    execution_logger.debug(
        f'Start batch execution of study case {args["execute"]} at {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}'
    )

    start_time = time.time()
    execution_logger.debug('Load study case data')

    loading_done = False
    with main_server.app.app_context():
        try:

            study_case_execution = StudyCaseExecution.query.filter(
                StudyCaseExecution.id.like(study_identifier)
            ).first()

            study = StudyCaseManager(study_case_execution.study_case_id)

            study.load_study_case_from_source()
            loading_done = True
        except:
            execution_logger.exception(
                'An error occurs during study case execution at loading time'
            )

            if study_case_execution is not None:
                study_case_execution.execution_status = StudyCaseExecution.FAILED
                main_server.db.session.add(study_case_execution)
                main_server.db.session.commit()

    if loading_done:
        elapsed_time = time.time() - start_time

        execution_logger.debug(f'study loading time : {elapsed_time} seconds')

        start_time = time.time()
        execution_logger.debug('Initializing execution strategy')

        exec_container = ExecutionEngineThread(study, execution_logger)

        elapsed_time = time.time() - start_time
        execution_logger.debug(
            f'Initializing execution strategy time : {elapsed_time} seconds'
        )

        # Call directly the run method to execute without thread
        # capabilities
        start_time = time.time()
        execution_logger.debug('Start execution')

        try:
            exec_container.run()

        except Exception as ex:
            execution_logger.exception(
                'An exception occurs during study case execution'
            )

        # disable execution handler
        # study.study_database_logger.flush()
        elapsed_time = time.time() - start_time
        execution_logger.debug(f'Execution time : {elapsed_time} seconds')

        trace_source_code(study.dump_directory, execution_logger)


def launch_generate_reference(reference_identifier):
    """
    Regenerate the reference given as identifier

    :param reference_identifier: reference to run
    """

    # Initialize generation logger with DEBUG logging output
    generation_log = logging.getLogger('sostrades_core')
    generation_log.setLevel(DEBUG)

    # Instantiate and attach database logger
    generation_log_handler = ReferenceMySQLHandler(reference_identifier)
    generation_log_handler.clear_reference_database_logs()
    generation_log.addHandler(generation_log_handler)

    # Then share handlers with GEMS logger to retrieve GEMS execution
    # message
    gems_logger = logging.getLogger("gemseo")
    for handler in generation_log.handlers:
        gems_logger.addHandler(handler)

    with main_server.app.app_context():

        start_time = time.time()

        generation_log.debug(
            f'Start batch generation of reference {reference_identifier} at {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}'
        )

        # Make sure that reference to regenerate is known in database
        reference_study = ReferenceStudy.query.filter(
            ReferenceStudy.id == reference_identifier
        ).first()

        if reference_study is None:
            message = f'Reference to regenerate not found in database, invalid identifier {reference_identifier})'
            generation_log.error(message)
            raise ReferenceStudyError(message)

        try:
            # Update reference study status
            ReferenceStudy.query.filter(ReferenceStudy.id == reference_study.id).update(
                {'execution_status': ReferenceStudy.RUNNING}
            )
            generation_log.debug(
                f'Update generation status to {ReferenceStudy.RUNNING}'
            )
            main_server.db.session.commit()

            generation_log.debug('Load Reference/Usecase')
            imported_module = import_module(reference_study.reference_path)
            imported_usecase = getattr(imported_module, 'Study')()
        except Exception as e:
            generation_log.exception(
                'The following error occurs during reference loading'
            )
            ReferenceStudy.query.filter(ReferenceStudy.id == reference_study.id).update(
                {
                    'execution_status': ReferenceStudy.FAILED,
                    'generation_logs': e,
                    'creation_date': None,
                }
            )
            main_server.db.session.commit()
            raise ReferenceStudyError(e)

        elapsed_time = time.time() - start_time

        generation_log.debug(
            f'Reference/Usecase loading time : {elapsed_time} seconds')

        start_time = time.time()
        generation_log.debug('Start Reference/Usecase generation...')

        try:
            reference_basepath = Config().reference_root_dir
            imported_usecase.set_dump_directory(reference_basepath)
            imported_usecase.load_data()
            imported_usecase.run(dump_study=True)

            ref_updated = ReferenceStudy.query.filter(
                ReferenceStudy.id == reference_identifier
            ).first()
            ref_updated.execution_status = ReferenceStudy.FINISHED
            ref_updated.creation_date = (
                datetime.now().astimezone(timezone.utc).replace(tzinfo=None)
            )
            main_server.db.session.add(ref_updated)
            main_server.db.session.commit()


            trace_source_code(imported_usecase.dump_directory, generation_log)
        except Exception as e:
            ReferenceStudy.query.filter(ReferenceStudy.id == reference_identifier).update(
                {
                    'execution_status': ReferenceStudy.FAILED,
                    'generation_logs': e,
                    'creation_date': None,
                }
            )
            generation_log.exception("An exception occurs during reference generation.")
            main_server.db.session.commit()
            raise ReferenceStudyError(e)

        elapsed_time = time.time() - start_time
        generation_log.debug(
            f'Reference/Usecase generation duration : {elapsed_time} seconds'
        )
        generation_log_handler.flush()


def trace_source_code(
    traceability_folder=None, logger=None, write_file=True, add_library_path=False
):
    """
    Regarding python path module information, extract and save all commit sha of
    repositories used to compute the study
    :param traceability_folder: folder to save the traceability file
    :type traceability_folder: str
    :param logger: logger for messages
    :type logger: Logger

    """

    if logger is None:
        logger = logging.getLogger(__name__)

    traceability_dict = {}

    # check for PYTHONPATH environment variable
    python_path_libraries = environ.get('PYTHONPATH')

    if python_path_libraries is not None and len(python_path_libraries) > 0:

        # Set to list each library of the PYTHONPATH
        libraries = python_path_libraries.split(pathsep)

        for library_path in libraries:
            if isdir(library_path):
                try:
                    repo = git.Repo(path=library_path, search_parent_directories=True)

                    # Retrieve url and remove connection info from it
                    raw_url = repo.remotes.origin.url
                    url = re.sub(INFO_REGEXP, INFO_REPLACE, raw_url)
                    try:
                        repo_name = url.split('.git')[0].split('/')[-1]
                    except:
                        print(f'Impossible to retrieve repo name from url {url}')
                        repo_name = url

                    branch = repo.active_branch
                    commit = branch.commit
                    commited_date = datetime.fromtimestamp(
                        commit.committed_date, timezone.utc
                    )

                    traceability_dict[repo_name] = {
                        URL: url,
                        BRANCH: branch.name,
                        COMMIT: commit.hexsha,
                        COMMITTED_DATE: commited_date.strftime("%d/%m/%Y %H:%M:%S"),
                    }
                    if add_library_path:
                        traceability_dict[repo_name][REPO_PATH] = library_path

                except git.exc.InvalidGitRepositoryError:
                    logger.debug(f'{library_path} folder is not a git folder')
                except Exception as error:
                    logger.debug(
                        f'{library_path} folder generates the following error while accessing with git:\n {str(error)}'
                    )
    if write_file and isdir(traceability_folder):
        with open(join(traceability_folder, 'traceability.yaml'), 'w') as file:
            yaml.dump(traceability_dict, file)

    return traceability_dict


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='SoSTrades commands.')

    parser.add_argument(
        '--execute',
        nargs='?',
        type=int,
        help='Execute the given study case execution id',
    )

    parser.add_argument(
        '--generate', nargs='?', type=int, help='Generate the given reference'
    )

    args = vars(parser.parse_args())

    if os.environ.get('SOS_TRADES_SERVER_CONFIGURATION') is None:
        dotenv_path = join(dirname(__file__), '.flaskenv')
        load_dotenv(dotenv_path)

    # Import server module after a basic configuration in order to set
    # correctly server  executing environment
    from sos_trades_api.server.split_mode import main_server
    from sos_trades_api.config import Config
    from sos_trades_api.tools.logger.reference_mysql_handler import (
        ReferenceMySQLHandler,
    )
    from sos_trades_api.models.database_models import ReferenceStudy, StudyCaseExecution
    from sos_trades_api.models.database_models import PodAllocation
    from importlib import import_module
    from sos_trades_api.tools.loading.study_case_manager import StudyCaseManager
    from sos_trades_api.tools.execution.execution_engine_thread import (
        ExecutionEngineThread,
    )

    if args['execute'] is not None:
        launch_calculation_study(args['execute'])
    elif args['generate'] is not None:
        launch_generate_reference(args["generate"])
