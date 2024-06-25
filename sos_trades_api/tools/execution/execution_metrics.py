'''
Copyright 2022 Airbus SAS
Modifications on 2024/06/07 Copyright 2024 Capgemini
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

import psutil

from sos_trades_api.config import Config
from sos_trades_api.controllers.sostrades_data.study_case_controller import get_study_case_allocation
from sos_trades_api.models.database_models import StudyCaseExecution, StudyCase
from sos_trades_api.server.base_server import app, db
from sos_trades_api.tools.kubernetes.kubernetes_service import kubernetes_get_pod_info

"""
Execution metric thread
"""

class ExecutionMetrics:
    """
    Class that manage execution metrics to store this change in the database for further treatment using the API
    """

    def __init__(self, study_case_execution_id):
        """
        Constructor
        :param study_case_execution_id: study case identifier in database (integer) use to
            identified the discipline to update in database
        """
        self.__study_case_execution_id = study_case_execution_id
        self.__started = True

        self.__thread = threading.Thread(target=self.__update_database)
        self.__thread.start()

    def stop(self):
        """
        Methods the stop the current thread
        """
        self.__started = False
        self.__thread.join()

    def __update_database(self):
        """
        Threaded methods to update the database without blocking execution process
        """
        # Infinite loop
        # The database connection is kept open
        while self.__started:
            # Add an exception manager to ensure that database eoor will not
            # shut down calculation
            try:
                # Open a database context
                with (((app.app_context()))):
                    study_case_execution = StudyCaseExecution.query.filter(StudyCaseExecution.id.like(self.__study_case_execution_id)).first()

                    config = Config()
                    if config.execution_strategy == Config.CONFIG_EXECUTION_STRATEGY_K8S:
                        study_case_allocation = get_study_case_allocation(study_case_execution.study_case_id)

                        # Retrieve memory and cpu from kubernetes
                        result = kubernetes_get_pod_info(study_case_allocation.kubernetes_pod_name, study_case_allocation.kubernetes_pod_namespace)

                        # Retrieve study case from database
                        study_case = StudyCase.query.filter(StudyCase.id.like(study_case_execution.study_case_id)).first()

                        # Retrieve limits of pod from config
                        cpu_limits = ''
                        memory_limits = ''
                        pod_execution_limit_from_config = app.config["CONFIG_FLAVOR_KUBERNETES"]["PodExec"][study_case.execution_pod_flavor]["limits"]
                        if pod_execution_limit_from_config is not None and pod_execution_limit_from_config["cpu"] is not None and pod_execution_limit_from_config["memory"]:
                            cpu_limits = pod_execution_limit_from_config["cpu"]
                            memory_limits = pod_execution_limit_from_config["memory"]

                        cpu_metric = f'{cpu_limits}'
                        memory_metric = f'{memory_limits} [GB]'
                        print(cpu_metric, memory_metric)

                    else:
                        # Check environment info
                        cpu_count_physical = psutil.cpu_count()
                        cpu_usage = round((psutil.cpu_percent() / 100) * cpu_count_physical, 2)
                        cpu_metric = f"{cpu_usage}/{cpu_count_physical}"

                        memory_count = round(psutil.virtual_memory()[0] / (1024 * 1024 * 1024), 2)
                        memory_usage = round(psutil.virtual_memory()[3] / (1024 * 1024 * 1024), 2)
                        memory_metric = f"{memory_usage}/{memory_count} [GB]"

                    study_case_execution.cpu_usage = cpu_metric
                    study_case_execution.memory_usage = memory_metric

                    db.session.add(study_case_execution)
                    db.session.commit()
            except Exception as ex:
                print(f"Execution metrics: {ex!s}")

            finally:
                # Wait 2 seconds before next metrics
                if self.__started:
                    time.sleep(2)
