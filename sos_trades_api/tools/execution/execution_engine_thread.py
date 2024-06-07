'''
Copyright 2022 Airbus SAS
Modifications on 2024/03/18 Copyright 2024 Capgemini

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
import threading
import time
from datetime import datetime, timedelta, timezone

from sostrades_core.execution_engine.proxy_discipline import ProxyDiscipline

from sos_trades_api.models.database_models import (
    StudyCase,
    StudyCaseDisciplineStatus,
    StudyCaseExecution,
)
from sos_trades_api.server.base_server import app, db
from sos_trades_api.tools.execution.execution_engine_observer import (
    ExecutionEngineObserver,
)
from sos_trades_api.tools.execution.execution_metrics import ExecutionMetrics


class ExecutionEngineThread(threading.Thread):

    def __init__(self, study_manager, execution_logger):
        threading.Thread.__init__(self)

        self.__study_case_id = study_manager.study.id

        # Persist execution identifier in case it change during run
        # (set of a new current execution in the study
        self.__study_case_execution_id = study_manager.study.current_execution_id
        self.__study_manager = study_manager
        self.__execution_logger = execution_logger

    def run(self):

        # set status at running:
        with app.app_context():
            study_case_execution = StudyCaseExecution.query.filter(
                StudyCaseExecution.id.like(self.__study_case_execution_id)).first()
            if study_case_execution is not None:
                study_case_execution.execution_status = StudyCaseExecution.RUNNING
                study_case_execution.message = ''
                db.session.add(study_case_execution)
                db.session.commit()
            else:
                study_case_execution.execution_status = StudyCaseExecution.FAILED
                study_case_execution.message = 'Execution id not found'
                db.session.add(study_case_execution)
                db.session.commit()
                self.__execution_logger.error('Execution id not found')
                execution_error = True
        
        execution_error = False
        start_time = time.time()
        self.__execution_logger.debug(
            'Clean database regarding execution status')

        elapsed_time = time.time() - start_time
        self.__execution_logger.debug(
            f'Cleaning time : {elapsed_time} seconds')

        start_time = time.time()
        self.__execution_logger.debug('Set status observer on each discipline')

        # List that store handler for discipline status observer
        status_observer = ExecutionEngineObserver(self.__study_case_id)
        execution_metrics = ExecutionMetrics(self.__study_case_execution_id)

        # Get each discipline and then assign a status observer to each one
        status_setup_list = []
        for disc_key, disc_value in self.__study_manager.execution_engine.dm.disciplines_dict.items():

            discipline = disc_value['reference']
            discipline.add_status_observer(status_observer)

            sce = StudyCaseDisciplineStatus()
            sce.study_case_id = self.__study_case_id
            sce.study_case_execution_id = self.__study_case_execution_id
            sce.discipline_key = discipline.get_disc_full_name()
            sce.status = ProxyDiscipline.STATUS_PENDING
            status_setup_list.append(sce)

        # Initialized record for each discipline
        with app.app_context():
            db.session.bulk_save_objects(status_setup_list)
            db.session.commit()

            # Give mapping between object identifier and discipline identifier to
            # the observer
            # It necessary to do another request because bulk save does not return
            # tuple identifier
            sce_list = StudyCaseDisciplineStatus.query\
                .filter(StudyCaseDisciplineStatus.study_case_id == self.__study_case_id)\
                .filter(StudyCaseDisciplineStatus.study_case_execution_id == self.__study_case_execution_id).all()

            identifier_mapping = {}
            for sce in sce_list:
                identifier_mapping[sce.discipline_key] = sce.id

            status_observer.set_object_mapping_id(identifier_mapping)

        elapsed_time = time.time() - start_time
        self.__execution_logger.debug(
            f'Observer setting time : {elapsed_time} seconds')

        try:
            # Execute current process
            start_time = time.time()
            self.__execution_logger.debug('Launch execution engine')

            self.__study_manager.run()

            elapsed_time = time.time() - start_time
            self.__execution_logger.debug(
                f'Execution engine calculation time : {elapsed_time} seconds')

        except Exception as error:
            self.__execution_logger.exception(
                f'The following exception occurs during execution.\n{str(error)}')
            execution_error = True

        finally:
            start_time = time.time()
            self.__execution_logger.debug(
                'Unsubscribe status observer on each discipline')

            # Unsubscribe each previously assign observer
            for disc_key, disc_value in self.__study_manager.execution_engine.dm.disciplines_dict.items():

                discipline = disc_value['reference']
                discipline.remove_status_observer(status_observer)

            status_observer.stop()
            execution_metrics.stop()

            elapsed_time = time.time() - start_time
            self.__execution_logger.debug(
                f'Observer unsubscribe time : {elapsed_time} seconds')

            with app.app_context():
                study_case_execution = StudyCaseExecution.query. \
                    filter(StudyCaseExecution.id.like(
                        self.__study_case_execution_id)).first()

                # Check if no stop has been requested
                # If it is the case then avoid to overwrite data
                if study_case_execution.execution_status == StudyCaseExecution.RUNNING:

                    try:
                        start_time = time.time()
                        self.__execution_logger.debug('Dump study case data')
                        # Persist data using the current persistance strategy
                        self.__study_manager.save_study_case()
                        self.__study_manager.save_study_read_only_mode_in_file()
                    except Exception as error:
                        self.__execution_logger.exception(
                            f'The following exception occurs during study dumping.\n{str(error)}')
                        execution_error = True
                    finally:
                        # Update study case execution status

                        self.__execution_logger.debug(
                            'Updating study case with finished status')
                        study_case = StudyCase.query.filter(
                            StudyCase.id.like(self.__study_case_id)).first()

                        # Update last modification date to make record to be
                        # updated
                        self.__execution_logger.info(
                            f'Study case modification date before update: {study_case.modification_date}')

                        new_modification_date = datetime.now().astimezone(
                            timezone.utc).replace(tzinfo=None)

                        # /!\ /!\ /!\ /!\
                        # When execution is externalize, some behaviour regarding host operating system
                        # has been observed.
                        # If the execution host date and the API host date setting are not the same
                        # Execution can be set to a date anterior to the one store in the host
                        # (cf. StudyCaseCache)
                        # A test is made regarding the new modification date, and if it is not posterior to the old one
                        # then a simple 5 seconds increment is done
                        if study_case.modification_date >= new_modification_date:
                            self.__execution_logger.warning(
                                f'Generated modification date ({new_modification_date}) is anterior to the old one, please check operating system timezone')
                            study_case.modification_date = study_case.modification_date + \
                                timedelta(seconds=5)
                        else:
                            study_case.modification_date = new_modification_date
                            self.__execution_logger.info(
                                f'New modification date: {study_case.modification_date}')
                        db.session.add(study_case)

                        study_case_execution = StudyCaseExecution.query.filter(
                            StudyCaseExecution.id.like(study_case.current_execution_id)).first()
                        study_case_execution.execution_status = StudyCaseExecution.FINISHED if not execution_error else StudyCaseExecution.FAILED
                        db.session.add(study_case_execution)
                        db.session.commit()

                        elapsed_time = time.time() - start_time
                        self.__execution_logger.debug(
                            f'Dump time : {elapsed_time} seconds')
                else:
                    self.__execution_logger.info(
                        f'Study interrupted, current state is not RUNNING but {study_case_execution.execution_status}')
