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
import sys
import argparse
import logging
from os.path import join, dirname
from datetime import datetime, timezone
from dotenv import load_dotenv


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='SoSTrades commands.')

    parser.add_argument('--execute', nargs='?', type=int,
                        help='Execute the given study case execution id')

    parser.add_argument('--generate', nargs='?', type=int,
                        help='Generate the given reference')

    args = vars(parser.parse_args())

    if os.environ.get('SOS_TRADES_SERVER_CONFIGURATION') is None:
        dotenv_path = join(dirname(__file__), '.flaskenv')
        load_dotenv(dotenv_path)

    # Import server module after a basic configuration in order to set
    # correctly server  executing environment
    from sos_trades_api import main_server
    from sos_trades_api.config import Config
    from sos_trades_core.tools.sos_logger import SoSLogging
    from sos_trades_api.base_server import PRODUCTION
    from sos_trades_api.tools.logger.reference_mysql_handler import ReferenceMySQLHandler
    from sos_trades_api.models.database_models import ReferenceStudy, StudyCaseExecution
    from importlib import import_module
    from sos_trades_api.tools.loading.study_case_manager import StudyCaseManager
    from sos_trades_api.tools.execution.execution_engine_thread import ExecutionEngineThread
    config = Config()

    # For development purpose assign envrionnement variable
    if os.environ['FLASK_ENV'] != PRODUCTION:

        if os.environ.get(config.execution_strategy_env_var) is None:
            if sys.platform == "win32":
                os.environ[config.execution_strategy_env_var] = 'subprocess'
            else:
                os.environ[config.execution_strategy_env_var] = 'subprocess'
            main_server.app.logger.info(
                f'value not found environment variable {config.execution_strategy_env_var}. Set it to default: {os.environ[config.execution_strategy_env_var]}')
        else:
            main_server.app.logger.info(
                f'value found environment variable {config.execution_strategy_env_var}: {os.environ[config.execution_strategy_env_var]}')


    # - Consistency check on server environment (every variables must be provided)
    if os.environ['FLASK_ENV'] == PRODUCTION:
        config.check()

    if args['execute'] is not None:

        # Initialize execution logger
        execution_logger = SoSLogging(
            'SoS', master=True, level=SoSLogging.INFO).logger

        study_case = None
        exec_engine = None

        execution_logger.debug(
            f'Start batch execution of study case {args["execute"]} at {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}')

        start_time = time.time()
        execution_logger.debug('Load study case data')

        loading_done = False
        with main_server.app.app_context():
            try:

                study_case_execution = StudyCaseExecution.query.filter(StudyCaseExecution.id.like(args["execute"])).first()

                study = StudyCaseManager(study_case_execution.study_case_id)
                study.add_execution_identifier = True
                study.study_database_logger.bulk_transaction = True

                # Attach logging handler to GEMS logger
                if study.study_database_logger is not None:
                    gems_logger = logging.getLogger("GEMS")

                    # disable execution handler
                    # gems_logger.addHandler(study.study_database_logger)

                study.load_data(display_treeview=False)
                study.load_disciplines_data()
                loading_done = True
            except:
                execution_logger.exception(
                    'An error occurs during study case execution at loading time')

                if study_case_execution is not None:
                    study_case_execution.execution_status = StudyCaseExecution.FAILED
                    main_server.db.session.add(study_case_execution)
                    main_server.db.session.commit()

        if loading_done:
            elapsed_time = time.time() - start_time

            execution_logger.debug(
                f'study loading time : {elapsed_time} seconds')

            start_time = time.time()
            execution_logger.debug('Initializing execution strategy')

            exec_container = ExecutionEngineThread(study, execution_logger)

            elapsed_time = time.time() - start_time
            execution_logger.debug(
                f'Initializing execution strategy time : {elapsed_time} seconds')

            # Call directly the run method to execute without thread
            # capabilities
            start_time = time.time()
            execution_logger.debug('Start execution')

            try:
                exec_container.run()

            except Exception as ex:
                execution_logger.exception(
                    'An exception occurs during study case execution')

            # disable execution handler
            # study.study_database_logger.flush()
            elapsed_time = time.time() - start_time
            execution_logger.debug(f'Execution time : {elapsed_time} seconds')

    elif args['generate'] is not None:
        # Initialize execution logger
        generation_log = SoSLogging(
            'SoS', master=True, level=SoSLogging.DEBUG).logger

        # Execution_log_handler
        generation_log_handler = ReferenceMySQLHandler(args["generate"])

        generation_log.addHandler(generation_log_handler)

        # If handlers has been define, link gems logger
        if generation_log.hasHandlers():

            # Then share handlers with GEMS logger to retrieve GEMS execution
            # message
            LOGGER = logging.getLogger("GEMS")
            for handler in generation_log.handlers:
                LOGGER.addHandler(handler)
        with main_server.app.app_context():
            generation_id = args["generate"]

            generation_log.debug(
                f'Start batch generation of reference {args["generate"]} at {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}')

            ref_gen_model = ReferenceStudy.query.filter(
                ReferenceStudy.id == generation_id).first()
            if ref_gen_model:
                ref_model_id = ref_gen_model.id
                usecase = ref_gen_model.reference_path
                ReferenceStudy.query.filter(ReferenceStudy.id == ref_model_id).update({
                    'execution_status': ReferenceStudy.RUNNING})
                main_server.db.session.commit()
                start_time = time.time()
                generation_log.debug('Load usecase')
                reference_basepath = Config().reference_root_dir
                loading_done = False

                try:
                    imported_module = import_module(usecase)
                    imported_usecase = getattr(imported_module, 'Study')()
                    loading_done = True
                except Exception as e:
                    generation_log.exception(
                        'An error occurs during usecase loading')
                    ReferenceStudy.query.filter(ReferenceStudy.id == ref_model_id).update(
                        {'execution_status': ReferenceStudy.FAILED, 'generation_logs': e})
                    main_server.db.session.commit()

                if loading_done:
                    elapsed_time = time.time() - start_time

                    generation_log.debug(
                        f'usecase loading time : {elapsed_time} seconds')

                    start_time = time.time()
                    generation_log.debug('Start generation...')
                    try:
                        imported_usecase.set_dump_directory(
                            reference_basepath)
                        imported_usecase.load_data()
                        imported_usecase.run(dump_study=True)

                        ref_updated = ReferenceStudy.query.filter(
                            ReferenceStudy.id == ref_model_id).first()
                        ref_updated.execution_status = ReferenceStudy.FINISHED
                        ref_updated.creation_date = datetime.now().\
                            astimezone(timezone.utc).replace(tzinfo=None)
                        main_server.db.session.add(ref_updated)
                        main_server.db.session.commit()
                    except Exception as e:
                        ReferenceStudy.query.filter(ReferenceStudy.id == ref_model_id).update(
                            {'execution_status': ReferenceStudy.FAILED,
                             'generation_logs': e,
                             'creation_date': None})

                        main_server.db.session.commit()
                    elapsed_time = time.time() - start_time
                    generation_log.debug(
                        f'Reference generation duration : {elapsed_time} seconds')
            else:
                generation_log.exception(
                    f'Unable to start generation of {args["generate"]}: element not found in database')
        generation_log_handler.flush()
    else:
        main_server.app.run(host='0.0.0.0', port='5000')
