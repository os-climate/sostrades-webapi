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
import threading

from sos_trades_api.config import Config
from sos_trades_api.models.database_models import StudyCaseAllocation
from sos_trades_api.tools.kubernetes import kubernetes_service
from sos_trades_api.server.base_server import app, db


def create_allocation(study_case_identifier):
    """
    Create a study case allocation instance in order to follow study case resource activation
    Save allocation in database to pass the allocation id to the thread that will launch kubernetes study pod
    Launch kubernetes service to build the study pod if the server_mode is kubernetes

    :param study_case_identifier: study case identifier to allocate
    :type study_case_identifier: int
    :return: sos_trades_api.models.database_models.StudyCaseAllocation
    """
    # create allocation in DB
    new_study_case_allocation = StudyCaseAllocation()
    new_study_case_allocation.study_case_id = study_case_identifier
    if Config().server_mode == Config.CONFIG_SERVER_MODE_MONO:
        new_study_case_allocation.status = StudyCaseAllocation.DONE
    elif Config().server_mode == Config.CONFIG_SERVER_MODE_K8S:
        new_study_case_allocation.status = StudyCaseAllocation.IN_PROGRESS
        new_study_case_allocation.kubernetes_pod_name = f'sostrades-study-server-{study_case_identifier}'

    db.session.add(new_study_case_allocation)
    db.session.commit()

    load_study_allocation(new_study_case_allocation)

    return new_study_case_allocation


def load_study_allocation(study_case_allocation):
    """
    Load service and deployment if they do not exists and wait for pod running in a thread
    """
    if Config().server_mode == Config.CONFIG_SERVER_MODE_K8S:
        #launch creation
        try:
            kubernetes_service.kubernetes_service_allocate(study_case_allocation.kubernetes_pod_name)
            study_case_allocation.status = get_allocation_status(study_case_allocation.kubernetes_pod_name)
            study_case_allocation.message = None
        except Exception as exception:
            study_case_allocation.status = StudyCaseAllocation.ERROR
            study_case_allocation.message = exception


def get_allocation_status(pod_name):
    """
    If server mode is kubernetes, check pod status and set the allocation status accordingly

    :param study_case_identifier: study case identifier to allocate
    :type study_case_identifier: int
    :return: sos_trades_api.models.database_models.StudyCaseAllocation status
    """
    status = ""
    if Config().server_mode == Config.CONFIG_SERVER_MODE_K8S:
        pod_status = kubernetes_service.kubernetes_study_service_pods_status(pod_name)
        if pod_status == "DONE":
            status = StudyCaseAllocation.DONE
        elif pod_status == "Running":
            status = StudyCaseAllocation.IN_PROGRESS
        else:
            raise "pod not found"
    else:
        status = StudyCaseAllocation.DONE

    return status

