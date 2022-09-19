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

    # First check that allocated resources does not already exist
    new_study_case_allocation = StudyCaseAllocation()
    new_study_case_allocation.study_case_id = study_case_identifier
    if Config().server_mode == Config.CONFIG_SERVER_MODE_MONO:
        new_study_case_allocation.status = StudyCaseAllocation.DONE
    elif Config().server_mode == Config.CONFIG_SERVER_MODE_K8S:
        new_study_case_allocation.status = StudyCaseAllocation.IN_PROGRESS

    db.session.add(new_study_case_allocation)
    db.session.commit()

    load_study_allocation(new_study_case_allocation.id)

    return new_study_case_allocation


def load_study_allocation(allocation_id):
    """
    Load service and deployment if they do not exists and wait for pod running in a thread
    """
    if Config().server_mode == Config.CONFIG_SERVER_MODE_K8S:
        # launch kubernetes after allocation creation
        _launch_kubernetes_allocation(allocation_id)


def _launch_kubernetes_allocation(allocation_id):
    #get allocation
    study_case_allocations = StudyCaseAllocation.query.filter(StudyCaseAllocation.id == allocation_id).all()

    if len(study_case_allocations) > 0:
        study_case_allocation = study_case_allocations[0]

        #launch creation
        try:
            study_case_allocation.kubernetes_pod_name = kubernetes_service.kubernetes_service_allocate(study_case_allocation.study_case_id)
            _retrieve_allocation_pod_status(study_case_allocation)
        except Exception as exception:
            study_case_allocation.status = StudyCaseAllocation.ERROR
            study_case_allocation.message = exception

        db.session.add(study_case_allocation)
        db.session.commit()



def get_allocation_status(study_case_identifier):
    """
    If server mode is kubernetes, check pod status and set the allocation status accordingly

    :param study_case_identifier: study case identifier to allocate
    :type study_case_identifier: int
    :return: sos_trades_api.models.database_models.StudyCaseAllocation status
    """
     # First check that allocated resources does not already exist
    study_case_allocations = StudyCaseAllocation.query.filter(StudyCaseAllocation.study_case_id == study_case_identifier).all()

    allocation = None
    if len(study_case_allocations) > 0:
        allocation = study_case_allocations[0]
        if Config().server_mode == Config.CONFIG_SERVER_MODE_K8S:
            _retrieve_allocation_pod_status(allocation)


    return allocation


def _retrieve_allocation_pod_status(study_case_allocation):
    try:
        pod_status = kubernetes_service.kubernetes_study_service_pods_status(study_case_allocation.kubernetes_pod_name)
        if pod_status.get(study_case_allocation.kubernetes_pod_name) == "running":
            study_case_allocation.status = StudyCaseAllocation.DONE
        else:
            study_case_allocation.status = StudyCaseAllocation.IN_PROGRESS
            study_case_allocation.message = "Pod not loaded"
    except Exception as exception:
        study_case_allocation.status = StudyCaseAllocation.ERROR
        study_case_allocation.message = exception

