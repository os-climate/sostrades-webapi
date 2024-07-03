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
import re
import psutil

from sos_trades_api.config import Config
from sos_trades_api.models.database_models import StudyCaseExecution, PodAllocation
from sos_trades_api.server.base_server import app, db
from sos_trades_api.tools.code_tools import extract_number_and_unit, convert_byte_into_byte_unit_targeted
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
                with app.app_context():
                    study_case_execution = StudyCaseExecution.query.filter(StudyCaseExecution.id.like(self.__study_case_execution_id)).first()
                    config = Config()
                    if config.execution_strategy == Config.CONFIG_EXECUTION_STRATEGY_K8S:
                        study_case_allocation = PodAllocation.query.filter(PodAllocation.identifier == study_case_execution.study_case_id).filter(
                                                        PodAllocation.pod_type == PodAllocation.TYPE_EXECUTION,
                                                        ).first()

                        # Retrieve limits of pod from config
                        cpu_limits = '----'
                        memory_limits = '----'
                        unit_byte_to_conversion = "GB"
                        pod_exec_memory_limit_from_config = app.config[Config.CONFIG_FLAVOR_KUBERNETES][Config.CONFIG_FLAVOR_POD_EXECUTION][study_case_allocation.flavor]["limits"]["memory"]
                        pod_exec_cpu_limit_from_config = app.config[Config.CONFIG_FLAVOR_KUBERNETES][Config.CONFIG_FLAVOR_POD_EXECUTION][study_case_allocation.flavor]["limits"]["cpu"]

                        if pod_exec_memory_limit_from_config is not None and pod_exec_cpu_limit_from_config:
                            # CPU limits
                            cpu_limits = str(''.join(re.findall(r'\d+', pod_exec_cpu_limit_from_config)))
                            # Retrieve and convert memory limits
                            if "mi" in pod_exec_memory_limit_from_config.lower():
                                unit_byte_to_conversion = "MB"

                            # Retrieve and extract limit and its unit
                            memory_limits_bit, memory_limits_unit_bit = extract_number_and_unit(pod_exec_memory_limit_from_config)
                            memory_limits_byte_converted = convert_byte_into_byte_unit_targeted(memory_limits_bit, memory_limits_unit_bit,
                                                                                 unit_byte_to_conversion)
                            if memory_limits_byte_converted is not None:
                                memory_limits = round(memory_limits_byte_converted, 2)

                            # Retrieve memory and cpu from kubernetes
                            result = kubernetes_get_pod_info(study_case_allocation.kubernetes_pod_name, study_case_allocation.kubernetes_pod_namespace, unit_byte_to_conversion)

                            cpu_metric = f'{result["cpu"]}/{cpu_limits}'
                            memory_metric = f'{result["memory"]}/{memory_limits} [{unit_byte_to_conversion}]'
                        else:
                            raise ValueError('Limit from configuration not found')

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