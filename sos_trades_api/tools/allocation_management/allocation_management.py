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
import os
import uuid
from datetime import datetime
from pathlib import Path

import yaml
from jinja2 import Template
from kubernetes import client

from sos_trades_api.config import Config
from sos_trades_api.models.database_models import PodAllocation, StudyCase
from sos_trades_api.server.base_server import app, db
from sos_trades_api.tools.kubernetes import kubernetes_service
from sos_trades_api.tools.kubernetes.kubernetes_service import (
    get_pod_name_from_event,
    get_pod_status_and_reason_from_event,
    kubernetes_create_deployment_and_service,
    kubernetes_create_pod,
    kubernetes_load_kube_config,
    watch_pod_events,
)


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
    # check that allocation already exists:
    pod_allocation = PodAllocation.query.filter(PodAllocation.identifier == identifier,
                                                PodAllocation.pod_type == allocation_type,
                                                ).first()
    if pod_allocation is None:
        pod_allocation = PodAllocation()

    pod_allocation.identifier = identifier
    pod_allocation.pod_status = PodAllocation.NOT_STARTED
    pod_allocation.pod_type = allocation_type
    pod_allocation.flavor = flavor
    pod_allocation.creation_date = datetime.now()


    #load allocation
    pod_allocation = load_allocation(pod_allocation, log_file_path)

    db.session.add(pod_allocation)
    db.session.commit()

    # refresh pod_allocation
    pod_allocation = PodAllocation.query.filter(PodAllocation.id == pod_allocation.id).first()
    return pod_allocation

def load_allocation(pod_allocation:PodAllocation, log_file_path=None):
    """
    launch pod creation with kubernetes API and get pod status if kubernetes strateg, else set status to DONE
    Then save pod allocation in DB

    """
    # create kubernete pod
    config = Config()
    identifier = pod_allocation.identifier
    save_identifier = pod_allocation.identifier
    save_pod_type = pod_allocation.pod_type
    # in case of execution allocation, the identifier is the study because
    # we want to have only one execution allocation by study (the current execution id)
    if pod_allocation.pod_type == PodAllocation.TYPE_EXECUTION:
        study = StudyCase.query.filter(StudyCase.id == identifier).first()
        if study is None:
            raise Exception("Study not Found")
        identifier = study.current_execution_id
    pod_name = get_pod_name(pod_allocation.identifier, pod_allocation.pod_type, execution_identifier=identifier)
    pod_allocation.kubernetes_pod_name = pod_name

    # get selected flavor
    flavors = None
    if pod_allocation.pod_type == PodAllocation.TYPE_STUDY and config.server_mode == Config.CONFIG_SERVER_MODE_K8S:
        flavors = config.kubernetes_flavor_config_for_study
    elif pod_allocation.pod_type in [PodAllocation.TYPE_EXECUTION, PodAllocation.TYPE_REFERENCE] and \
        config.execution_strategy == Config.CONFIG_EXECUTION_STRATEGY_K8S:
        flavors = config.kubernetes_flavor_config_for_exec

    #Select default value of flavor in case of the value doesn't exist
    flavor = None
    if flavors is not None and len(flavors) > 0:
        if pod_allocation.flavor not in flavors:
            pod_allocation.flavor = list(flavors.keys())[0]
        flavor = flavors[pod_allocation.flavor]

    try:
        if pod_allocation.pod_type == PodAllocation.TYPE_STUDY and config.server_mode == Config.CONFIG_SERVER_MODE_K8S:
            k8_service = get_kubernetes_jinja_config(pod_name, config.service_study_server_filepath, flavor)
            k8_deployment = get_kubernetes_jinja_config(pod_name, config.deployment_study_server_filepath, flavor)
            pod_allocation.kubernetes_pod_namespace = k8_deployment["metadata"]["namespace"]
            db.session.add(pod_allocation)
            db.session.commit()
            pod_allocation = PodAllocation.query.filter(PodAllocation.identifier == save_identifier,
                                                PodAllocation.pod_type == save_pod_type,
                                                ).first()
            kubernetes_create_deployment_and_service(k8_service, k8_deployment)

        elif pod_allocation.pod_type != PodAllocation.TYPE_STUDY and config.execution_strategy == Config.CONFIG_EXECUTION_STRATEGY_K8S:
            k8_conf = get_kubernetes_config_eeb(pod_name, identifier, pod_allocation.pod_type, flavor, log_file_path)
            pod_allocation.kubernetes_pod_namespace = k8_conf["metadata"]["namespace"]
            db.session.add(pod_allocation)
            db.session.commit()
            pod_allocation = PodAllocation.query.filter(PodAllocation.identifier == save_identifier,
                                                PodAllocation.pod_type == save_pod_type,
                                                ).first()

            kubernetes_create_pod(k8_conf)
        else:
            pod_allocation.flavor = ""
            pod_allocation.pod_status = PodAllocation.RUNNING
            pod_allocation.message = ""
    except Exception as exp:
        pod_allocation.pod_status = PodAllocation.IN_ERROR
        pod_allocation.message = f"error while pod creation: {exp!s}"



    return pod_allocation

def get_image_digest_from_api_pod():
    """
    Get the image digest of the current pod. The result depends on the "K8S_NAMESPACE" and "HOSTNAME" environment variables within that pod. And we suppose that the pod has only one container
    """
    kubernetes_load_kube_config() # Load kubeconfig rights
    v1 = client.CoreV1Api() # Create a client API
    namespace = os.getenv("K8S_NAMESPACE") # Get the current pod namespace
    pod_name = os.getenv("HOSTNAME") # Get the current pod name
    digest=v1.read_namespaced_pod(name=pod_name, namespace=namespace).status.container_statuses[0].image_id # Return the pod image digest used, depends on the current pod name and namepsace
    return digest

def get_kubernetes_config_eeb(pod_name, identifier, pod_type, flavor, log_file_path=None):
    """
    Get pod configuration
    """
    k8_conf = None
    eeb_k8_filepath = Config().eeb_filepath
    if Path(eeb_k8_filepath).exists():
        app.logger.debug("pod configuration file found")
        with open(eeb_k8_filepath) as f:
            k8_conf = yaml.safe_load(f)

        if k8_conf is not None:
            # Overload pod configuration file
            k8_conf["metadata"]["name"] = pod_name
            if flavor is not None:
                k8_conf["spec"]["containers"][0]["resources"] = flavor
            if pod_type == PodAllocation.TYPE_EXECUTION:
                k8_conf["spec"]["containers"][0]["args"] = [
                    "--execute", str(identifier), log_file_path]
            if pod_type == PodAllocation.TYPE_REFERENCE:
                k8_conf["spec"]["containers"][0]["args"] = [
                "--generate", str(identifier)]
            # Allow to create eeb with the same image_id than the API server
            image_id=get_image_digest_from_api_pod()
            if image_id is not None:
                k8_conf["spec"]["containers"][0]["image"] = image_id # We suppose that the pod has only one container
            app.logger.debug(k8_conf)
    return k8_conf

def get_kubernetes_jinja_config(pod_name, file_path, flavor):
    """
    Get config kubernetes file from jinja template to be rendered with pod_name
    """
    k8_conf = None
    with open(file_path) as f:
        k8_tplt = Template(f.read())
        if flavor is not None:
            k8_tplt = k8_tplt.render(pod_name=pod_name, flavor=flavor)
        else:
            k8_tplt = k8_tplt.render(pod_name=pod_name)
        k8_conf = yaml.safe_load(k8_tplt)
        # Allow to create study pod with the same image_id than the API server
        image_id=get_image_digest_from_api_pod()
        if image_id is not None and k8_conf["kind"]=="Deployment":
            k8_conf["spec"]["template"]["spec"]["containers"][0]["image"] = image_id # We suppose that the pod has only one container
        app.logger.debug(k8_conf)
    return k8_conf

def get_pod_name(identifier, pod_type, execution_identifier):
    """
    build pod name depending on type
    :param identifier: id of the study in case of type STUDY, id of referenceStudy in case of REFERENCE, or StudyCaseExecutionId in case of EXECUTION
    :type identifier: int
    :param pod_type: type of the pod allocation: STUDY, REFERENCE or EXECUTION
    :type pod_type: str
    :param identifier: id of the execution in case of type EXECUTION, id of referenceStudy in case of REFERENCE, or StudyCaseExecutionId in case of EXECUTION
    :type identifier: int
    """
    if pod_type == PodAllocation.TYPE_STUDY:
        return f"sostrades-study-server-{identifier}"

    elif pod_type == PodAllocation.TYPE_EXECUTION:
        # retrieve execution id

        return f"eeb-sc{identifier}-e{execution_identifier}-{uuid.uuid4()}"

    elif pod_type == PodAllocation.TYPE_REFERENCE:
        return f"generation-g{identifier}-{uuid.uuid4()}"

def get_allocation_status(pod_allocation:PodAllocation):
    """
    If server mode is kubernetes, check pod status and set the allocation status accordingly, save status in DB

    :param study_case_identifier: study case identifier to allocate
    :type study_case_identifier: int
    :return: sos_trades_api.models.database_models.PodAllocation status and reason (str)
    """
    config = Config()
    if not config.pod_watcher_activated:
        status = ""
        reason = ""
        if (pod_allocation.pod_type == PodAllocation.TYPE_STUDY and config.server_mode == Config.CONFIG_SERVER_MODE_K8S) or \
            (pod_allocation.pod_type != PodAllocation.TYPE_STUDY and config.execution_strategy == Config.CONFIG_EXECUTION_STRATEGY_K8S):
            if pod_allocation.kubernetes_pod_name is not None and pod_allocation.kubernetes_pod_namespace is not None:
                try:
                    pod_phase, reason = kubernetes_service.kubernetes_service_pod_status(pod_allocation.kubernetes_pod_name, pod_allocation.kubernetes_pod_namespace, pod_allocation.pod_type != PodAllocation.TYPE_STUDY)

                    status, reason = get_status_from_pod_phase(pod_phase, reason)



                except Exception as ex:
                    status = PodAllocation.IN_ERROR
                    reason = f"Error while retrieving status: {ex!s}"

            else:
                status = PodAllocation.NOT_STARTED
        else:
            status = PodAllocation.RUNNING
            reason = ""

        return status, reason
    else:
        return pod_allocation.pod_status, pod_allocation.message

def get_status_from_pod_phase(pod_phase, reason):
    status = PodAllocation.IN_ERROR
    if reason == "OOMKilled":
        status = PodAllocation.OOMKILLED
    elif pod_phase == "Running":
        status = PodAllocation.RUNNING
    elif pod_phase == "Pending":
        status = PodAllocation.PENDING
    elif pod_phase == "Succeeded":
        status = PodAllocation.COMPLETED
    elif pod_phase == "Failed":
        status = PodAllocation.IN_ERROR
    elif pod_phase is None:
        status = PodAllocation.NOT_STARTED
        reason = "Pod not found"
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
        allocation_name = pod_allocation.kubernetes_pod_name
        # delete allocation object
        db.session.delete(pod_allocation)
        db.session.flush()
        # delete pod
        if delete_pod_needed:
            kubernetes_service.kubernetes_delete_pod(pod_allocation.kubernetes_pod_name, pod_allocation.kubernetes_pod_namespace)
    except Exception as ex:
        db.session.rollback()
        raise ex

    db.session.commit()
    app.logger.info(f"PodAllocation {allocation_name} have been successfully deleted")


def update_all_pod_status():
    """
    For all allocations 
    """
    config = Config()
    if config.pod_watcher_activated:

        # retreive namespace
        namespace = None
        if config.server_mode == Config.CONFIG_SERVER_MODE_K8S:
            k8_deployment = get_kubernetes_jinja_config("pod_name", config.deployment_study_server_filepath, None)
            namespace = k8_deployment["metadata"]["namespace"]
        elif config.execution_strategy == Config.CONFIG_EXECUTION_STRATEGY_K8S:
            k8_conf = get_kubernetes_config_eeb("pod_name", 1, PodAllocation.TYPE_EXECUTION, None, "log_file_path")
            namespace = k8_conf["metadata"]["namespace"]

        for event in watch_pod_events(app.logger, namespace):

            # get if pod name is in allocations
            pod_name = get_pod_name_from_event(event)
            if pod_name.startswith("sostrades-study-server"):
                # retreive the service name by removing the uuid of the pod name
                names = pod_name.split("-")[0:4]
                pod_name = "-".join(names)

            with app.app_context():
                allocations = PodAllocation.query.filter(PodAllocation.kubernetes_pod_name == pod_name).all()
                allocation = None
                updated = False
                if allocations is not None and len(allocations) > 0:
                    if len(allocations) > 1:
                        # get the oldest, delete others
                        allocation = max(allocations, key=lambda x: x.creation_date)
                        for alloc in allocations:
                            if alloc != allocation:
                                db.session.delete(alloc)
                    else:
                        allocation = allocations[0]
                if allocation is not None:
                    pod_phase, reason = get_pod_status_and_reason_from_event(event)
                    pod_status, reason = get_status_from_pod_phase(pod_phase, reason)

                    if pod_status != allocation.pod_status or reason != allocation.message:
                        # delete service and deployment in case of study oomkilled
                        if pod_status == PodAllocation.OOMKILLED and allocation.pod_type == PodAllocation.TYPE_STUDY:
                            kubernetes_service.kubernetes_delete_deployment_and_service(allocation.kubernetes_pod_name, allocation.kubernetes_pod_namespace)

                        # update allocation status in db
                        allocation.pod_status = pod_status
                        allocation.message = reason
                        db.session.add(allocation)
                        updated = True

                db.session.commit()
                if updated:
                    app.logger.info(f"updated pod_status {pod_name}: {allocation.pod_status}, {allocation.message}")
    else:
        # old watcher
        with app.app_context():
            updated_allocation = []
            all_allocations = PodAllocation.query.all()
            for allocation in all_allocations:
                if allocation.pod_status in [PodAllocation.NOT_STARTED, PodAllocation.RUNNING, PodAllocation.PENDING]:
                    allocation.pod_status, allocation.message = get_allocation_status(allocation)
                    updated_allocation.append(allocation.kubernetes_pod_name)
                    db.session.add(allocation)
            db.session.commit()
            if len(updated_allocation) > 0:
                app.logger.debug(f"Updated pod status: {', '.join(updated_allocation)}")


def clean_all_allocations_type_study():
    # delete all allocations
    study_case_allocations = PodAllocation.query.filter(PodAllocation.pod_type == PodAllocation.TYPE_STUDY).all()
    delete_study_server_services_and_deployments(study_case_allocations)

def clean_all_allocations_type_reference(logger):
    # delete all allocations with pod_type = REFERENCE
    reference_allocations = PodAllocation.query.filter(PodAllocation.pod_type == PodAllocation.TYPE_REFERENCE).all()
    for ref_alloc in reference_allocations:
        db.session.delete(ref_alloc)
    db.session.commit()
    logger.info(f"{len(reference_allocations)} reference allocations have been deleted")
