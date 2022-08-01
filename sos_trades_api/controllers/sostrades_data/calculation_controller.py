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
from sos_trades_api.controllers.sostrades_data.study_case_controller import get_logs, get_raw_logs
from sos_trades_api.tools.code_tools import file_tail

"""
mode: python; py-indent-offset: 4; tab-width: 4; coding: utf-8
Calculation case Functions
"""
import logging
from datetime import datetime, timezone
import os
import signal
import threading
from sos_trades_api.models.calculation_dashboard import CalculationDashboard
from sos_trades_api.models.database_models import StudyCase, StudyCaseDisciplineStatus, \
    StudyCaseExecutionLog, StudyCaseExecution, Process, StudyCaseLog
from sos_trades_api.controllers.error_classes import InvalidStudy
from sos_trades_api.models.loaded_study_case_execution_status import LoadedStudyCaseExecutionStatus
from sos_trades_api.tools.execution.execution_engine_subprocess import ExecutionEngineSubprocess
from sos_trades_api.tools.execution.execution_engine_kubernetes import ExecutionEngineKubernetes
from sos_trades_api.tools.execution.execution_engine_thread import ExecutionEngineThread
from sos_trades_api.controllers.sostrades_main.ontology_controller import load_processes_metadata, \
    load_repositories_metadata
from sos_trades_api.config import Config
from sos_trades_api.base_server import db, app
from sos_trades_api.tools.loading.study_case_manager import StudyCaseManager
from sos_trades_core.api import get_sos_logger
from sqlalchemy.sql.expression import and_

calculation_semaphore = threading.Semaphore()


class CalculationError(Exception):
    """Base StudyCase Exception"""

    def __init__(self, msg=None):
        Exception.__init__(self, msg)

    def __str__(self):
        return self.__class__.__name__ + '(' + Exception.__str__(self) + ')'


def execute_calculation(study_id, username):
    """
        Given a study case identifier, prepare study execution
        Check are done regarding execution of the study case (one at a time)

        :param study_id: study case to run
        :type int

        :param username: user that request execution
        :type str

    """

    try:
        calculation_semaphore.acquire()

        config = Config()

        # Retrieve StudyCase object to get current execution and check
        # its status
        study_case = StudyCase.query.filter(
            StudyCase.id.like(study_id)).first()

        if study_case.current_execution_id is not None:
            # Retrieve execution object related to study to check status
            study_case_execution = StudyCaseExecution.query\
                .filter(StudyCaseExecution.id == study_case.current_execution_id).first()

            if study_case_execution is not None and study_case_execution.execution_status == StudyCaseExecution.RUNNING:
                calculation_semaphore.release()
                raise CalculationError('Study already submitted.\nIt must be stopped/terminated before running a new one.')

        # Create a new execution entry and associate it to the study
        new_study_case_execution = StudyCaseExecution()
        new_study_case_execution.study_case_id = study_case.id
        new_study_case_execution.execution_status = StudyCaseExecution.RUNNING
        new_study_case_execution.creation_date = datetime.now().astimezone(
            timezone.utc).replace(tzinfo=None)
        new_study_case_execution.requested_by = username

        db.session.add(new_study_case_execution)
        db.session.flush()

        study_case.current_execution_id = new_study_case_execution.id

        db.session.add(study_case)

        # Clearing all log regarding the given study case
        StudyCaseLog.query\
            .filter(StudyCaseLog.study_case_id == study_id)\
            .delete()
        db.session.commit()
        # Clearing all execution log regarding the given study case
        # But only log that does not rely to calculation (null study_case_execution_id key)
        StudyCaseExecutionLog.query\
            .filter(StudyCaseExecutionLog.study_case_id == study_id)\
            .filter(StudyCaseExecutionLog.study_case_execution_id == None)\
            .delete()
        db.session.commit()

        # Once the process is validated, then generate the corresponding data
        # manager using execution engine class
        study = StudyCaseManager(study_id)

        # Create backup file if it does not exists
        study.study_case_manager_save_backup_files()

        if config.execution_strategy == Config.CONFIG_EXECUTION_STRATEGY_THREAD:

            # Initialize execution logger
            execution_logger = get_sos_logger('SoS')

            # If handlers has been define, link gems logger
            if execution_logger.hasHandlers():

                # Then share handlers with GEMS logger to retrieve GEMS execution
                # message
                LOGGER = logging.getLogger("GEMS")
                for handler in execution_logger.handlers:
                    LOGGER.addHandler(handler)

            # Load study data if not loaded
            study.load_data(display_treeview=False)
            study.load_disciplines_data()
            study.load_cache()

            exec_thread = ExecutionEngineThread(study, execution_logger)
            exec_thread.start()
        elif config.execution_strategy == Config.CONFIG_EXECUTION_STRATEGY_SUBPROCESS:
            log_file = study.raw_log_file_path_absolute()
            exec_subprocess = ExecutionEngineSubprocess(study.study.current_execution_id, log_file)
            pid = exec_subprocess.run()
            new_study_case_execution.execution_type = StudyCaseExecution.EXECUTION_TYPE_PROCESS
            new_study_case_execution.process_identifier = pid
            db.session.add(new_study_case_execution)
            db.session.commit()
        elif config.execution_strategy == Config.CONFIG_EXECUTION_STRATEGY_K8S:
            log_file = study.raw_log_file_path_relative()
            exec_kubernetes = ExecutionEngineKubernetes()
            pod_name = exec_kubernetes.run(study.study, log_file)
            new_study_case_execution.execution_type = StudyCaseExecution.EXECUTION_TYPE_K8S
            new_study_case_execution.kubernetes_pod_name = pod_name
            db.session.add(new_study_case_execution)
            db.session.commit()

        else:
            raise CalculationError(
                f'Unknown calculation strategy : {config.execution_strategy}')

        app.logger.info(
            f'Start execution request: successfully submit study case {study_id} using {config.execution_strategy} strategy')

        calculation_semaphore.release()

    except Exception as error:

        calculation_semaphore.release()

        # Update execution before submitted process
        study_case_execution = StudyCaseExecution.query.filter(
            and_(StudyCaseExecution.study_case_id == study_id, StudyCaseExecution.execution_status == StudyCaseExecution.RUNNING)).first()

        if study_case_execution is not None:
            study_case_execution.execution_status = StudyCaseExecution.FAILED
            db.session.add(study_case_execution)
            db.session.commit()

        app.logger.exception(
            f'Start execution request: failed to submit study case {study_id} using {config.execution_strategy} strategy')

        raise CalculationError(error)


def stop_calculation(study_case_id, study_case_execution_id=None):
    """
        Stop a running study case calculation
        Stopping a study case is asynchronous, everything is up to date in database but regarding stop latency between
        environment, the procedure does wait for the achievement of the stop

        :param study_case_id: study case to stop
        :param study_case_execution_id: study case execution to stop specifically (if none the current one associated to
        the study will be used)
    """

    # Once the process is validated, then generate the corresponding data
    # manager using execution engine class

    # Retrieving study case data
    study_case = StudyCase.query.filter(
        StudyCase.id.like(study_case_id)).first()

    if study_case_execution_id is None:
        study_case_execution_id = study_case.current_execution_id

    # If no execution registered on study case object, then there is nothing to stop
    if study_case is None:
        raise InvalidStudy(
            f'Requested study case (identifier {study_case_id} does not exist in the database')

    if study_case_execution_id is not None:
        # Retrieve execution object related to study to check status
        study_case_execution = StudyCaseExecution.query.filter(
            StudyCaseExecution.id.like(study_case_execution_id)).first()

        if study_case_execution is not None:
            try:
                app.logger.info(f'study_case_execution found with info:\n{study_case_execution.execution_type}\n{study_case_execution.kubernetes_pod_name}')
                if study_case_execution.execution_type == StudyCaseExecution.EXECUTION_TYPE_K8S and \
                        len(study_case_execution.kubernetes_pod_name) > 0:
                    exec_kubernetes = ExecutionEngineKubernetes()
                    exec_kubernetes.delete(study_case_execution.kubernetes_pod_name)
                elif study_case_execution.execution_type == StudyCaseExecution.EXECUTION_TYPE_PROCESS and \
                        study_case_execution.process_identifier > 0:
                    try:
                        os.kill(study_case_execution.process_identifier, signal.SIGTERM)
                    except Exception as ex:
                        app.logger.exception(f'This error occurs when trying to kill process {study_case_execution.process_identifier}')

                # Update execution
                study_case_execution.execution_status = StudyCaseExecution.STOPPED
                db.session.add(study_case_execution)
                db.session.commit()

            except Exception as error:

                # Update execution before submitted process
                study_case_execution.execution_status = StudyCaseExecution.FAILED
                db.session.add(study_case_execution)
                db.session.commit()

                raise CalculationError(error)


def calculation_status(study_id):
    """
    Retrieve the execution status of a study
    """
    study_case = StudyCase.query.filter(
        StudyCase.id.like(study_id)).first()

    if study_case is not None:

        # Check associated execution object
        if study_case.current_execution_id is not None:
            study_case_execution = StudyCaseExecution.query.filter(StudyCaseExecution.id.like(study_case.current_execution_id)).first()

            # In case execution has been deleted an study not updated
            if study_case_execution is not None:

                status = study_case_execution.execution_status
                cpu_usage = study_case_execution.cpu_usage
                memory_usage = study_case_execution.memory_usage

                config = Config()

                if config.execution_strategy == 'kubernetes' and \
                        study_case_execution.execution_type is StudyCaseExecution.EXECUTION_TYPE_K8S and \
                        len(study_case_execution.kubernetes_pod_name) > 0:

                    if not study_case_execution.execution_status == StudyCaseExecution.PENDING and \
                            not study_case_execution.execution_status == StudyCaseExecution.RUNNING:
                        exec_kubernetes = ExecutionEngineKubernetes()
                        exec_kubernetes.delete(study_case_execution.kubernetes_pod_name)

                        study_case_execution.kubernetes_pod_name = ''
                        db.session.add(study_case_execution)
                        db.session.commit()
                    else:
                        exec_kubernetes = ExecutionEngineKubernetes()
                        status = exec_kubernetes.pods_status(
                            [study_case_execution.kubernetes_pod_name])

                        if study_case_execution.execution_status == StudyCaseExecution.RUNNING and status[study_case_execution.kubernetes_pod_name] == 'Failed':
                            study_case_execution.execution_status = StudyCaseExecution.FAILED
                            db.session.add(study_case_execution)
                            db.session.commit()

                sce_list = StudyCaseDisciplineStatus.query\
                    .filter(StudyCaseDisciplineStatus.study_case_id == study_case.id)\
                    .filter(StudyCaseDisciplineStatus.study_case_execution_id == study_case.current_execution_id).all()

                disciplines_status_dict = {}
                for sce in sce_list:
                    disciplines_status_dict[sce.discipline_key] = sce.status

                return LoadedStudyCaseExecutionStatus(study_id, disciplines_status_dict, status, cpu_usage, memory_usage)

        return LoadedStudyCaseExecutionStatus(study_id, {}, '', '----', '----')

    else:
        raise InvalidStudy(
            f'Requested study case (identifier {study_id} does not exist in the database')


def calculation_logs(study_case_id, study_case_execution_id=None):
    """
        Retrieve execution logs from database for a given study case

    :param study_case_id: study case identifier
    :param study_case_execution_id: execution identifier (optional)

    :return: StudyCaseExecutionLog[]
    """
    if study_case_id is not None:
        result = []
        try:

            study_case = StudyCase.query.filter(
                StudyCase.id.like(study_case_id)).first()

            if study_case is None:
                raise InvalidStudy(f'Requested study case (identifier {study_case_id} does not exist in the database')

            file_path = get_raw_logs(study_id=study_case_id)
            if os.path.isfile(file_path):
                result = file_tail(file_path, 200)

        except Exception as ex:
            print(ex)
        finally:
            return result

    else:
        raise InvalidStudy(
            f'Requested study case (identifier {study_case_id} does not exist in the database')


def calculation_raw_logs(study_case_id, study_case_execution_id):
    """
    Retrieve execution logs from database for a given study case

    :param study_case_id: study case identifier
    :param study_case_execution_id: execution identifier

    :return: str (local filepath)
    """
    if study_case_id is not None and study_case_execution_id is not None:
        file_path = ''
        try:

            study_case = StudyCase.query.filter(
                StudyCase.id.like(study_case_id)).first()

            if study_case is None:
                raise InvalidStudy(f'Requested study case (identifier {study_case_id} does not exist in the database')

            if study_case_execution_id is None:
                study_case_execution_id = study_case.current_execution_id

            study = StudyCaseManager(study_case_id)

            file_path = study.raw_log_file_path_absolute(study_case_execution_id)

        except Exception as ex:
            print(ex)
        finally:
            return file_path

    else:
        raise InvalidStudy(
            f'Requested study case (identifier {study_case_id} does not exist in the database')


def get_calculation_dashboard():
    """
    Retrieve all the study cases, groups names running
    """

    # Get existing process name
    all_process = Process.query.all()

    process_names = []
    repository_names = []

    for process in all_process:
        process_names.append(f'{process.process_path}.{process.name}')
        repository_names.append(process.process_path)

    processes_metadata = load_processes_metadata(process_names)

    repository_metadata = load_repositories_metadata(repository_names)

    execution_history = db.session\
        .query(StudyCase.id, StudyCase.name, StudyCaseExecution.id,
               StudyCaseExecution.creation_date, StudyCase.repository, StudyCase.process,
               StudyCaseExecution.requested_by, StudyCaseExecution.execution_status)\
        .filter(StudyCaseExecution.study_case_id == StudyCase.id).all()

    result = []
    for rs in execution_history:

        repository_display_name = rs[4]
        if rs[4] in repository_metadata:
            repository_display_name = repository_metadata[repository_display_name]['label']

        process_display_name = f'{rs[4]}.{rs[5]}'
        if repository_display_name in processes_metadata:
            process_display_name = processes_metadata[repository_display_name]['label']

        new_calculation_dashboard = CalculationDashboard(
            rs[0], rs[1], rs[2], rs[3], rs[4], rs[5], repository_display_name, process_display_name, rs[6], rs[7])
        result.append(new_calculation_dashboard)

    return result


def delete_calculation_entry(study_case_id, study_case_execution_id):
    """

    :param study_case_id: study case related to the execution
    :param study_case_execution_id: study case execution to delete
    :return: void
    """
    if study_case_id is not None and study_case_execution_id is not None:

        study_case = StudyCase.query.filter(StudyCase.id == study_case_id).first()

        if study_case is not None:
            if study_case.current_execution_id == study_case_execution_id:
                study_case.current_execution_id = None
                db.session.add(study_case)

            StudyCaseExecution.query\
                .filter(StudyCaseExecution.id == study_case_execution_id)\
                .filter(StudyCaseExecution.study_case_id == study_case_id)\
                .delete()
            db.session.commit()
        else:
            raise InvalidStudy(
                f'Study case execution (identifier {study_case_id}/{study_case_execution_id} does not exist in the database')
    else:
        raise InvalidStudy(
            f'Study case execution (identifier {study_case_id}/{study_case_execution_id} does not exist in the database')


