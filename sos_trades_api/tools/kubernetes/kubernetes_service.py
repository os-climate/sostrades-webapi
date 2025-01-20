'''
Copyright 2022 Airbus SAS
Modifications on 2023/07/19-2023/11/20 Copyright 2023 Capgemini

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
import time
from functools import partial

import urllib3
from kubernetes import client, config, watch

from sos_trades_api.server.base_server import app
from sos_trades_api.tools.code_tools import (
    convert_byte_into_byte_unit_targeted,
    extract_number_and_unit,
)

"""
Execution engine kubernete
"""

class ExecutionEngineKuberneteError(Exception):
    """Base StudyCase Exception"""

    def __init__(self, msg=None):
        Exception.__init__(self, msg)

    def __str__(self):
        return self.__class__.__name__ + "(" + Exception.__str__(self) + ")"

def kubernetes_create_pod(k8_conf):
    """
    create a pod with kubernetes api
    :param k8_conf: config of the pod to launch
    :type k8_conf: yaml config file content
    """
    pod_name = k8_conf["metadata"]["name"]
    pod_namespace = k8_conf["metadata"]["namespace"]

    app.logger.debug("--------------------")
    app.logger.debug("pod settings : ")
    app.logger.debug(f"name : {pod_name}")
    app.logger.debug(
        f'target image : {k8_conf["spec"]["containers"][0]["image"]}')

    start_time = time.time()
    # Create k8 api client object
    kubernetes_load_kube_config()

    api_instance = client.CoreV1Api(client.ApiClient())
    elapsed_time = time.time() - start_time
    app.logger.debug(f"K8 api config time : {elapsed_time}")

    start_time = time.time()
    api_instance.create_namespaced_pod(body=k8_conf, namespace=pod_namespace)
    elapsed_time = time.time() - start_time
    app.logger.debug(f"K8 api pod submission : {elapsed_time}")

    start_time = time.time()
    while True:
        resp = api_instance.read_namespaced_pod(name=pod_name,
                                                namespace=pod_namespace)

        if resp.status.phase is not None:
            break
        time.sleep(1)
    elapsed_time = time.time() - start_time
    app.logger.debug(f"K8 api pod pending : {elapsed_time}")

    return pod_name


def kubernetes_create_deployment_and_service(k8_service_conf, k8_deployment_conf):
    """
    Launch kubernetes service to build the study pod if the server_mode is Kubernetes

    :param study_case_identifier: study case identifier to allocate
    :type study_case_identifier: int
    :return: The state of the kubernetes services
    """
    # Create k8 api client object
    kubernetes_load_kube_config()
    core_api_instance = client.CoreV1Api(client.ApiClient())
    apps_api_instance = client.AppsV1Api(client.ApiClient())

    kubernetes_service_create(k8_service_conf, core_api_instance)
    kubernetes_deployment_create(k8_deployment_conf, apps_api_instance)


def kubernetes_service_create(k8_service_conf, core_api_instance):
    """
    create a kubernetes service with selected config if the service doesn't already exists
    :param k8_service_conf: config of the service
    :type k8_service_conf: yaml config file content
    :param core_api_instance: api instance of 
    :type core_api_instance: yaml config file content
    """
    pod_name = k8_service_conf["metadata"]["name"]
    namespace = k8_service_conf["metadata"]["namespace"]

    # check service existance
    service_found = False
    try:
        resp = core_api_instance.read_namespaced_service(name=pod_name, namespace=namespace)
        service_found = True
    except client.rest.ApiException as api_exception:
        if api_exception.status == 404:
            app.logger.info("Service not found")
        else:
            raise api_exception

    # create service
    if not service_found:
        resp = core_api_instance.create_namespaced_service(body=k8_service_conf, namespace=namespace)
        print(resp)
        # wait while service is created
        interval_s = 1
        max_s = 600
        current_waiting_s = 0
        while current_waiting_s < max_s:
            try:
                core_api_instance.read_namespaced_service_status(name=pod_name, namespace=namespace)
                break
            except client.rest.ApiException as api_exception:
                if api_exception.status == 404:
                    app.logger.info("Service not found")
                else:
                    raise api_exception
            time.sleep(interval_s)
            current_waiting_s += interval_s
    else:
        app.logger.info("Service already exist")


def kubernetes_deployment_create(k8_deploy_conf, apps_api_instance):
    """
    create a kubernetes deployment with selected config if the deployment doesn't already exists

    :param k8_deploy_conf: config of the service
    :type k8_deploy_conf: yaml config file content
    :param apps_api_instance: api instance of 
    :type apps_api_instance: yaml config file content
    """
    pod_name = k8_deploy_conf["metadata"]["name"]
    namespace = k8_deploy_conf["metadata"]["namespace"]

    # check deployment existance
    deployement_found = False
    try:
        apps_api_instance.read_namespaced_deployment(name=pod_name, namespace=namespace)
        deployement_found = True
    except client.rest.ApiException as api_exception:
        if api_exception.status == 404:
            app.logger.info("Deployment not found")
        else:
            raise api_exception

    # create deployment
    if not deployement_found:
        apps_api_instance.create_namespaced_deployment(body=k8_deploy_conf, namespace=namespace)
        # wait while deployment is created
        interval_s = 1
        max_s = 600
        current_waiting_s = 0
        while current_waiting_s < max_s:
            try:
                apps_api_instance.read_namespaced_deployment_status(name=pod_name, namespace=namespace)
                break
            except client.rest.ApiException as api_exception:
                if api_exception.status == 404:
                    app.logger.info("Deployment not found")
                else:
                    raise api_exception
            time.sleep(interval_s)
            current_waiting_s += interval_s
    else:
        app.logger.info("deployement already exist")


def kubernetes_delete_pod(pod_name, pod_namespace):
    """
    kill a pod with kubernetes api
    :param pod_name: name of the pod to kill
    :type pod_name: str
    :param pod_namespace: namespace of the pod to kill
    :type pod_namespace: str
    """
    # Create k8 api client object
    kubernetes_load_kube_config()

    api_instance = client.CoreV1Api(client.ApiClient())

    resp = api_instance.delete_namespaced_pod(name=pod_name, namespace=pod_namespace)
    app.logger.info(f"k8s response : {resp}")




def kubernetes_service_pod_status(pod_or_service_name:str, pod_namespace:str, is_pod_name_complete:bool=True)->str:
    """
    check pod status
    :param pod_or_service_name: pod name or service name (set is_pod_name_complete to false in case of service name)
    :param pod_namespace: namespace k8 where to find the pod
    :param is_pod_name_complete: boolean to test if the pod_or_service_name is exactly the pod name or just the begining of the name
    :return: status (str) and reason (str) of pod
    """
    result = None
    reason = None

    # Create k8 api client object
    kubernetes_load_kube_config()

    api_instance = client.CoreV1Api(client.ApiClient())

    pod_list = api_instance.list_namespaced_pod(namespace=pod_namespace)
    for pod in pod_list.items:
        if pod.status is not None and pod.metadata is not None and pod.metadata.name is not None and (pod.metadata.name == pod_or_service_name or \
            (not is_pod_name_complete and pod.metadata.name.startswith(f"{pod_or_service_name}-"))):

            result = pod.status.phase
            reason = get_container_error_reason(pod)

            # Check case the pod has restarted with error or oomkilled
            # (restart_count > 0 => it has a deployment)
            if pod.status is not None and pod.status.container_statuses is not None and len(pod.status.container_statuses) > 0:
                container_status = pod.status.container_statuses[0]

                if (container_status.restart_count > 0 and \
                    container_status.last_state is not None and \
                    container_status.last_state.terminated is not None):
                    result = "Failed"
                    reason = container_status.last_state.terminated.reason

                    # delete the service and deployment in case of service name
                    if not is_pod_name_complete:
                        kubernetes_delete_deployment_and_service(pod_or_service_name, pod_namespace)
            break

    return result, reason

def get_container_error_reason(pod):
    """
    get reason if error in pod
    :param pod:pod to check
    :type pod: pod api client
    :return: message reason
    :return type: str
    """
    status = None
    # get the container status
    if pod.status is not None and pod.status.container_statuses is not None and len(pod.status.container_statuses) > 0:
        container_status = pod.status.container_statuses[0]
        # check status
        if container_status.ready is False:
            waiting_state = container_status.state.waiting
            terminated_state = container_status.state.terminated

            # if status in error get the reason
            if waiting_state is not None and waiting_state.reason is not None:
                status = waiting_state.reason
            if terminated_state is not None and terminated_state.reason is not None:
                status = terminated_state.reason
    return status


sos_kube_configured = False
def kubernetes_load_kube_config():
    global sos_kube_configured

    if not sos_kube_configured:
        # load k8 api rights config or incluster config
        try:
            config.load_kube_config()
            sos_kube_configured = True
        except:
            try:
                config.load_incluster_config()  # How to set up the client from within a k8s pod
                sos_kube_configured = True
            except config.config_exception.ConfigException as error:
                message = f"Could not configure kubernetes python client : {error}"
                app.logger.error(message)
                raise ExecutionEngineKuberneteError(message)


def kubernetes_get_pod_info(pod_name: str, pod_namespace: str, unit_byte_to_conversion: str) -> dict:
    """

    :Summary:
           Get pod usage info like cpu and memory

    :Args:
        pod_name (str): unique name of the pod => metadata.name
        pod_namespace (str): namespace where is the pod
        unit_byte_to_conversion (str) : unit in byte targeted
        cpu_limits (int) : limit of cpu from configuration

    :return:
        dict of cpu usage and memory usage
    """

    result = {}

    # Create k8 api client object
    kubernetes_load_kube_config()
    try:

        v1 = client.CoreV1Api()
        pods = v1.list_namespaced_pod(pod_namespace)

        target_pod = None
        for pod in pods.items:
            if pod.metadata.name == pod_name:
                target_pod = pod
                break
        if target_pod:
            print(f"pod '{target_pod.metadata.name}' is '{target_pod.status.phase}'")
            if target_pod.status.phase == "Running":
                api = client.CustomObjectsApi()
                resources = api.list_namespaced_custom_object(
                    group="metrics.k8s.io",
                    version="v1beta1",
                    namespace=pod_namespace,
                    plural="pods",
                )

                print(f"Pods list :{resources['items']}")
                pod_searched = list(filter(lambda pod: pod["metadata"]["name"] == pod_name, resources["items"]))
                if len(pod_searched) > 0:

                    # Retrieve cpu (in nanocores) and unit and convert it in CPU
                    pod_cpu_nanocores, pod_cpu_unit = extract_number_and_unit(pod_searched[0]["containers"][0]["usage"]["cpu"])
                    pod_cpu = round(pod_cpu_nanocores / 1e9, 2)

                    # Retrieve memory usage and convert it to gigabit
                    pod_memory_kib, pod_memory_unit = extract_number_and_unit(pod_searched[0]["containers"][0]["usage"]["memory"])

                    pod_memory_converted = convert_byte_into_byte_unit_targeted(pod_memory_kib, pod_memory_unit, unit_byte_to_conversion)

                    result["cpu"] = pod_cpu
                    result["memory"] = round(pod_memory_converted, 2)

                    return result
                else:
                    raise ExecutionEngineKuberneteError(f"Pod '{pod_name}' from CustomObjectsApi not found")
            else:
                raise ExecutionEngineKuberneteError(f"Pod '{target_pod}' is not running. Status : {target_pod.status.phase}")
        else:
            raise ExecutionEngineKuberneteError(f"Pod '{pod_name}' from CoreV1Api not found")

    except Exception as error:
        message = f"Unable to retrieve pod metrics: {error}"
        app.logger.error(message)
        raise ExecutionEngineKuberneteError(message)

def kubernetes_delete_deployment_and_service(pod_name, pod_namespace):
    """
    delete service and deployment, this will kill the asssociated pod
    :param pod_name: pod_name to delete
    :type pod_name: str

    :param pod_namespace: namespace where are the pods
    :type pod_namespace: str
    """
    # Create k8 api client object
    kubernetes_load_kube_config()

    core_api_instance = client.CoreV1Api(client.ApiClient())
    apps_api_instance = client.AppsV1Api(client.ApiClient())

    # check service existance
    service_found = False
    try:
        core_api_instance.read_namespaced_service(name=pod_name, namespace=pod_namespace)
        service_found = True
    except client.rest.ApiException as api_exception:
        if api_exception.status == 404:
            print("Not found")
    # delete service
    if service_found:
        try:
            resp = core_api_instance.delete_namespaced_service(name=pod_name, namespace=pod_namespace)

        except Exception as api_exception:
            app.logger.error(api_exception)

    # check deployment existance
    deployement_found = False
    try:
        apps_api_instance.read_namespaced_deployment(name=pod_name, namespace=pod_namespace)
        deployement_found = True
    except client.rest.ApiException as api_exception:
        if api_exception.status == 404:
            print("Not found")
    # delete deployment
    if deployement_found:
        try:
            resp = apps_api_instance.delete_namespaced_deployment(name=pod_name, namespace=pod_namespace)

        except Exception as api_exception:
            app.logger.error(api_exception)


def watch_pod_events(logger, namespace):
    # Create k8 api client object   
    kubernetes_load_kube_config()
    logger.info(f"Starting watcher for namespace: {namespace}")
    core_api_instance = client.CoreV1Api(client.ApiClient())
    w = watch.Watch()
    try:
        for event in w.stream(partial(core_api_instance.list_namespaced_pod, namespace=namespace, timeout_seconds=3600, _request_timeout=60)):
            if event['object']['metadata']['name'].startswith('eeb') or \
                event['object']['metadata']['name'].startswith('sostrades-study-server') or\
                event['object']['metadata']['name'].startswith('generation') :

                yield event

        logger.info("Finished namespace stream.")
    except urllib3.exceptions.ReadTimeoutError:
        #time out, the watcher will be restarted
        logger.info("Expected timeout in stream to retrieve pod events.")
        pass



def get_pod_name_from_event(event):
    return event["object"]["metadata"]["name"]

def get_pod_status_and_reason_from_event(event):
    status_phase = event["object"]["status"]["phase"]
    reason = ""
    status = event["object"]["status"]
    container_statuses = status.get("containerStatuses")
    if status is not None and container_statuses is not None and len(container_statuses) > 0:
        container_status = container_statuses[0]
        # check status
        if container_status.get("ready") is False:
            waiting_state = container_status.get("state").get("waiting")
            terminated_state = container_status.get("state").get("terminated")
            running_state = container_status.get("state").get("running")

            if running_state is not None:
                # the container is up but the server is not ready
                status_phase = "Pending"

            # if status in error get the reason
            if waiting_state is not None and waiting_state.get("reason") is not None:
                reason = waiting_state["reason"]
            if terminated_state is not None and terminated_state.get("reason") is not None:
                reason = terminated_state["reason"]

        if (container_status.get("restartCount") > 0 and \
            container_status.get("lastState") is not None and \
            container_status.get("lastState").get("terminated") is not None):
            status_phase = "Failed"
            reason = container_status.get("lastState").get("terminated").get("reason")

    return status_phase, reason
