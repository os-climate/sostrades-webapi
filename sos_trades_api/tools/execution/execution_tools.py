'''
Copyright 2024 Capgemini
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
from sos_trades_api.models.database_models import PodAllocation, StudyCaseExecution
from sos_trades_api.server.base_server import db
from sos_trades_api.tools.allocation_management.allocation_management import (
    get_allocation_status,
)


def update_study_case_execution_status(study_case_id: int, study_case_execution: StudyCaseExecution):
    """
    Update execution status by checking the pod allocation status
    """
    pod_allocation = PodAllocation.query.filter(PodAllocation.identifier == study_case_id).filter(
                                                PodAllocation.pod_type == PodAllocation.TYPE_EXECUTION,
                                                ).first()

    if pod_allocation is not None:
        pod_allocation.pod_status, pod_allocation.message = get_allocation_status(pod_allocation)

    if pod_allocation is not None and (study_case_execution.execution_status in [StudyCaseExecution.RUNNING, StudyCaseExecution.PENDING, StudyCaseExecution.POD_PENDING]):

        # if the computation has failed the error message is in the logs
        if (study_case_execution.execution_status == StudyCaseExecution.RUNNING
                and pod_allocation.pod_status != PodAllocation.RUNNING):
            study_case_execution.execution_status = StudyCaseExecution.FAILED
        # if the pod has failed, the error message is in the pod allocation
        if pod_allocation.pod_status in [PodAllocation.IN_ERROR, PodAllocation.OOMKILLED]:
            study_case_execution.execution_status = StudyCaseExecution.POD_ERROR
            if pod_allocation.message is not None and pod_allocation.message != "":
                if pod_allocation.pod_status == PodAllocation.OOMKILLED:
                    study_case_execution.message = f"Pod had not enough resources (current size {pod_allocation.flavor}), choose a bigger execution pod size"
                else:
                    study_case_execution.message = f"Pod is in error : {pod_allocation.message}"
                    # the message of study case execution has 64 lenght
                    if len(study_case_execution.message) > 60:
                        study_case_execution.message = study_case_execution.message[0:61] + "..."
            else:
                study_case_execution.message = "Pod is in error : unknown error"

        # if the pod is pending, get the reason in message
        # (the execution status will be set at running by the execution pod once it is loaded)
        elif pod_allocation.pod_status == PodAllocation.PENDING:
            study_case_execution.execution_status = StudyCaseExecution.POD_PENDING
            if pod_allocation.message is not None and pod_allocation.message != "":
                study_case_execution.message = f"Pod is loading : {pod_allocation.message}"
                # the message of study case execution has 64 lenght
                if len(study_case_execution.message) > 60:
                    study_case_execution.message = study_case_execution.message[0:61] + "..."
            else:
                study_case_execution.message = "Pod is loading"
        elif pod_allocation.pod_status == PodAllocation.RUNNING and study_case_execution.execution_status == StudyCaseExecution.POD_PENDING:
            study_case_execution.message = "Pod is up, computation should start soon"
            study_case_execution.execution_status = StudyCaseExecution.PENDING


        db.session.add(study_case_execution)
        db.session.commit()

