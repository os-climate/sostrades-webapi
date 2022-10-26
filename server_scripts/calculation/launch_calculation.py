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
# coding: utf-8
import os
import time
import argparse
import logging
from os.path import join, dirname
from datetime import datetime, timezone
from dotenv import load_dotenv
from logging import DEBUG


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
    execution_logger = get_sos_logger('SoS')

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

            study.load_data(display_treeview=False)
            study.load_disciplines_data()
            study.load_cache()
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


def launch_generate_reference(reference_identifier):
    """
    Regenerate the reference given as identifier

    :param reference_identifier: reference to run
    """

    # Initialize generation logger with DEBUG logging output
    generation_log = get_sos_logger('SoS')
    generation_log.setLevel(DEBUG)

    # Instantiate and attach database logger
    generation_log_handler = ReferenceMySQLHandler(reference_identifier)
    generation_log.addHandler(generation_log_handler)

    # Then share handlers with GEMS logger to retrieve GEMS execution
    # message
    gems_logger = logging.getLogger("GEMS")
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
                'The follozing error occurs during reference loading'
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

        generation_log.debug(f'Reference/Usecase loading time : {elapsed_time} seconds')

        start_time = time.time()
        generation_log.debug('Start Reference/Usecase generation...')

        try:
            reference_basepath = Config().reference_root_dir
            imported_usecase.set_dump_directory(reference_basepath)
            imported_usecase.load_data()
            imported_usecase.run(dump_study=True)

            ref_updated = ReferenceStudy.query.filter(
                ReferenceStudy.id == reference_study.id
            ).first()
            ref_updated.execution_status = ReferenceStudy.FINISHED
            ref_updated.creation_date = (
                datetime.now().astimezone(timezone.utc).replace(tzinfo=None)
            )
            main_server.db.session.add(ref_updated)
            main_server.db.session.commit()
        except Exception as e:
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
            f'Reference/Usecase generation duration : {elapsed_time} seconds'
        )
        generation_log_handler.flush()


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
    from sos_trades_api import main_server
    from sos_trades_api.config import Config
    from sos_trades_core.api import get_sos_logger
    from sos_trades_api.tools.logger.reference_mysql_handler import (
        ReferenceMySQLHandler,
    )
    from sos_trades_api.models.database_models import ReferenceStudy, StudyCaseExecution
    from importlib import import_module
    from sos_trades_api.tools.loading.study_case_manager import StudyCaseManager
    from sos_trades_api.tools.execution.execution_engine_thread import (
        ExecutionEngineThread,
    )

    if args['execute'] is not None:
        launch_calculation_study(args['execute'])
    elif args['generate'] is not None:
        launch_generate_reference(args["generate"])
