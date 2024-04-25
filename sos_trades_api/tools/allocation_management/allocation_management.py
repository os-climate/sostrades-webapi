'''
Copyright 2022 Airbus SAS
Modifications on 2023/11/06-2023/11/24 Copyright 2023 Capgemini

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
import uuid

from jinja2 import Template
from sos_trades_api.tools.kubernetes.kubernetes_service import kubernetes_create_deployment_and_service, kubernetes_create_pod

import yaml

from sos_trades_api.config import Config
from sos_trades_api.models.database_models import PodAllocation
from sos_trades_api.tools.kubernetes import kubernetes_service
from sos_trades_api.server.base_server import app, db
from pathlib import Path



def create_and_load_allocation(identifier:int, allocation_type:str, flavor:str, log_file_path:str=None)->PodAllocation:
    """
    Create a study case allocation instance in order to follow study case resource activation
    Save allocation in database to pass the allocation id to the thread that will launch kubernetes pod
    Launch kubernetes service to build the pod if the server_mode is kubernetes

    :param identifier: identifier of the element to allocate, 
                        id of the study in case of type STUDY, 
                        id of referenceStudy in case of REFERENCE, 
                        or StudyCaseExecution Id in case of EXECUTION
    :type identifier: int
    :param allocation_type: type of pod allocation into [STUDY, REFERENCE, EXECUTION]
    :type allocation_type: str
    :param flavor: selected flavor for the pod allocation
    :type flavor: str
    :param log_file_path:log file path (for execution)
    :type log_file_path: str
    
    :return: sos_trades_api.models.database_models.PodAllocation
    """
    # create allocation
    new_pod_allocation = PodAllocation()
    new_pod_allocation.identifier = identifier
    new_pod_allocation.pod_status = PodAllocation.NOT_STARTED
    new_pod_allocation.pod_type = allocation_type
    new_pod_allocation.flavor = flavor
    
    
    #load allocation
    new_pod_allocation = load_allocation(new_pod_allocation, log_file_path)
    app.logger.info("Retrieved status of pod of kubernetes from create_and_load_allocation()")
    
    db.session.add(new_pod_allocation)
    db.session.commit()

    # refresh pod_allocation
    new_pod_allocation = PodAllocation.query.filter(PodAllocation.id == new_pod_allocation.id).first()
    return new_pod_allocation

def load_allocation(pod_allocation:PodAllocation, log_file_path=None):
    '''
    launch pod creation with kubernetes API and get pod status if kubernetes strateg, else set status to DONE
    Then save pod allocation in DB

    '''
    # create kubernete pod
    config = Config()
    pod_name = get_pod_name(pod_allocation.identifier, pod_allocation.pod_type)
    pod_allocation.kubernetes_pod_name = pod_name

    # get selected flavor
    flavors = config.kubernetes_flavor_config
    flavor = None
    if flavors is not None and len(flavors) > 0:
        if pod_allocation.flavor not in flavors:
            pod_allocation.flavor = list(flavors.keys())[0]
        flavor = flavors[pod_allocation.flavor]

    try:
        if pod_allocation.pod_type == PodAllocation.TYPE_STUDY and config.server_mode == Config.CONFIG_SERVER_MODE_K8S:
            k8_service = get_kubernetes_jinja_config(pod_name, config.service_study_server_filepath, flavor)
            k8_deployment = get_kubernetes_jinja_config(pod_name, config.deployment_study_server_filepath, flavor)
            kubernetes_create_deployment_and_service(k8_service, k8_deployment)
            pod_allocation.kubernetes_pod_namespace = k8_deployment['metadata']['namespace']
            pod_allocation.pod_status, pod_allocation.message = get_allocation_status(pod_allocation)
        
        elif pod_allocation.pod_type != PodAllocation.TYPE_STUDY and config.execution_strategy == Config.CONFIG_EXECUTION_STRATEGY_K8S:
            k8_conf = get_kubernetes_config_eeb(pod_name, pod_allocation.identifier, pod_allocation.pod_type, flavor, log_file_path)
            kubernetes_create_pod(k8_conf)
            pod_allocation.kubernetes_pod_namespace = k8_conf['metadata']['namespace']
            pod_allocation.pod_status, pod_allocation.message = get_allocation_status(pod_allocation)
        else: 
            pod_allocation.flavor = ''
            pod_allocation.pod_status = PodAllocation.RUNNING
            pod_allocation.message = ""
    except Exception as exp:
        pod_allocation.pod_status = PodAllocation.IN_ERROR
        pod_allocation.message = f'error while pod creation: {str(exp)}'

    

    return pod_allocation



def get_kubernetes_config_eeb(pod_name, identifier, pod_type, flavor, log_file_path=None):
    """
    Get pod configuration
    """
    k8_conf = None
    eeb_k8_filepath = Config().eeb_filepath

    if Path(eeb_k8_filepath).exists():
        app.logger.debug(f'pod configuration file found')
        with open(eeb_k8_filepath) as f:
            k8_conf = yaml.safe_load(f)

        if k8_conf is not None:
            # Overload pod configuration file
            k8_conf['metadata']['name'] = pod_name
            if flavor is not None:
                k8_conf['spec']['containers'][0]['resources'] = flavor
            if pod_type == PodAllocation.TYPE_EXECUTION:
                k8_conf['spec']['containers'][0]['args'] = [
                    '--execute', str(identifier), log_file_path]
            if pod_type == PodAllocation.TYPE_REFERENCE:
                k8_conf['spec']['containers'][0]['args'] = [
                '--generate', str(identifier)]
    return k8_conf

def get_kubernetes_jinja_config(pod_name, file_path, flavor):
    '''
    Get config kubernetes file from jinja template to be rendered with pod_name
    '''
    k8_conf = None
    with open(file_path) as f:
        k8_tplt = Template(f.read())
        if flavor is not None:
            k8_tplt = k8_tplt.render(pod_name=pod_name, flavor=flavor)
        else:
            k8_tplt = k8_tplt.render(pod_name=pod_name)
        k8_conf = yaml.safe_load(k8_tplt)
    return k8_conf
   
def get_pod_name(identifier, pod_type):
    '''
    build pod name depending on type
    :param identifier: id of the study in case of type STUDY, id of referenceStudy in case of REFERENCE, or StudyCaseExecutionId in case of EXECUTION
    :type identifier: int
    :param pod_type: type of the pod allocation: STUDY, REFERENCE or EXECUTION
    :type pod_type: str
    '''
    if pod_type == PodAllocation.TYPE_STUDY:
        return f'sostrades-study-server-{identifier}'
    
    elif pod_type == PodAllocation.TYPE_EXECUTION:
        return f'eeb-e{identifier}-{uuid.uuid4()}'
    
    elif pod_type == PodAllocation.TYPE_REFERENCE:
        return f'generation-g{identifier}-{uuid.uuid4()}'

def get_allocation_status(pod_allocation:PodAllocation):
    """
    If server mode is kubernetes, check pod status and set the allocation status accordingly, save status in DB

    :param study_case_identifier: study case identifier to allocate
    :type study_case_identifier: int
    :return: sos_trades_api.models.database_models.PodAllocation status and reason (str)
    """
    status = ""
    reason = ""
    if (pod_allocation.pod_type == PodAllocation.TYPE_STUDY and Config().server_mode == Config.CONFIG_SERVER_MODE_K8S) or \
        (pod_allocation.pod_type != PodAllocation.TYPE_STUDY and Config().execution_strategy == Config.CONFIG_EXECUTION_STRATEGY_K8S):
        if pod_allocation.kubernetes_pod_name is not None and pod_allocation.kubernetes_pod_namespace is not None:
            try:
                pod_status, reason = kubernetes_service.kubernetes_service_pod_status(pod_allocation.kubernetes_pod_name, pod_allocation.kubernetes_pod_namespace, pod_allocation.pod_type != PodAllocation.TYPE_STUDY)
                if reason == "OOMKilled":
                    status = PodAllocation.OOMKILLED
                elif pod_status == "Running":
                    status = PodAllocation.RUNNING
                elif pod_status == "Pending":
                    status = PodAllocation.PENDING
                elif pod_status == "Succeeded":
                    status = PodAllocation.COMPLETED
                elif pod_status == "Failed":
                    status = PodAllocation.IN_ERROR
                elif pod_status is None:
                    status = PodAllocation.NOT_STARTED
                    reason = "Pod not found"
                else:
                    status = PodAllocation.IN_ERROR
            except Exception as ex:
                status = PodAllocation.IN_ERROR
                reason = f'Error while retrieving status: {str(ex)}'
            
        else:
            status = PodAllocation.NOT_STARTED
    else:
        status = PodAllocation.RUNNING
        reason = ""
    
    return status, reason

def delete_study_server_services_and_deployments(study_case_allocations:list[PodAllocation]):
    """
    Delete study allocations, delete associated service and deployment in case of kubernetes server mode
    :param study_case_allocations: list of podAllocation to delete
    :type study_case_allocations: PodAllocation list
    """
    try:

        # delete service and deployment
        for pod_allocation in study_case_allocations:
            if (pod_allocation.pod_type == PodAllocation.TYPE_STUDY and Config().server_mode == Config.CONFIG_SERVER_MODE_K8S) or \
                (pod_allocation.pod_type != PodAllocation.TYPE_STUDY and Config().execution_strategy == Config.CONFIG_EXECUTION_STRATEGY_K8S):
                kubernetes_service.kubernetes_delete_deployment_and_service(pod_allocation.kubernetes_pod_name, pod_allocation.kubernetes_pod_namespace)
        for alloc in study_case_allocations:
            # delete allocation object
            db.session.delete(alloc)
        db.session.commit()
    except Exception as ex:
        raise ex
        

def delete_pod_allocation(pod_allocation:PodAllocation, delete_pod_needed):
    """
    Delete a pod allocations, delete associated pod in case if delete_pod_needed
    :param pod_allocation: podAllocation to delete
    :type pod_allocation: PodAllocation 
    :param delete_pod_needed: if the pod needs to be deleted (for exemple if we are in execution mode kubernetes)
    :type delete_pod_needed: boolean
    """
    try:
        # delete allocation object
        db.session.delete(pod_allocation)
        db.session.flush()
        # delete pod
        if delete_pod_needed:
            kubernetes_service.kubernetes_delete_pod(pod_allocation.kubernetes_pod_name, pod_allocation.kubernetes_pod_namespace)
    
        app.logger.info(f"PodAllocation {pod_allocation.kubernetes_pod_name} have been successfully deleted")
    except Exception as ex:
        db.session.rollback()
        raise ex
    
    db.session.commit()
        

def update_all_pod_status():
    """
    For all allocations 
    """
    with app.app_context():
        updated_allocation = []
        all_allocations = PodAllocation.query.all()
        for allocation in all_allocations:
            if allocation.pod_status != PodAllocation.COMPLETED:
                allocation.pod_status, allocation.message = get_allocation_status(allocation)
                updated_allocation.append(allocation.kubernetes_pod_name)
                db.session.add(allocation)
        db.session.commit()
        if len(updated_allocation) > 0:
            app.logger.debug(f"Updated pod status: {', '.join(updated_allocation)}")


def clean_all_allocations_services_and_deployments():
    # delete all allocations
    study_case_allocations = PodAllocation.query.filter(PodAllocation.pod_type == PodAllocation.TYPE_STUDY).all()
    delete_study_server_services_and_deployments(study_case_allocations)
    