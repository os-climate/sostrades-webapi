'''
Copyright 2022 Airbus SAS
Modifications on 2023/07/19-2023/11/03 Copyright 2023 Capgemini

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
"""
mode: python; py-indent-offset: 4; tab-width: 4; coding: utf-8
Execution engine kubernete
"""
from kubernetes import client, config
from sos_trades_api.config import Config
from sos_trades_api.server.base_server import app
from jinja2 import Template
from pathlib import Path
import uuid
import yaml
import time
import requests


class ExecutionEngineKuberneteError(Exception):
    """Base StudyCase Exception"""

    def __init__(self, msg=None):
        Exception.__init__(self, msg)

    def __str__(self):
        return self.__class__.__name__ + '(' + Exception.__str__(self) + ')'


def kubernetes_service_run(study, log_file_path):
    """

    :param study: Study object to run
    :param log_file_path: file to redirect stdout and stderr
    :return:
    """

    # Retrieve the kubernetes configuration file regarding execution
    # engine block
    eeb_k8_filepath = Config().eeb_filepath

    if Path(eeb_k8_filepath).exists():

        app.logger.debug(f'pod configuration file found')

        k8_conf = None
        with open(eeb_k8_filepath) as f:
            k8_conf = yaml.safe_load(f)

        if k8_conf is not None:

            # Overload pod configuration file
            pod_name = f'{k8_conf["metadata"]["name"]}-sc{study.id}-e{study.current_execution_id}-{uuid.uuid4()}'
            pod_namespace = k8_conf['metadata']['namespace']
            k8_conf['metadata']['name'] = pod_name
            k8_conf['spec']['containers'][0]['args'] = [
                '--execute', str(study.current_execution_id), log_file_path]

            app.logger.debug(f'--------------------')
            app.logger.debug(f'pod settings : ')
            app.logger.debug(f'name : {pod_name}')
            app.logger.debug(f'executed sce : {study.current_execution_id}')
            app.logger.debug(f'output log : {log_file_path}')
            app.logger.debug(
                f'target image : {k8_conf["spec"]["containers"][0]["image"]}')

            start_time = time.time()
            # Create k8 api client object
            try:
                config.load_kube_config()
            except IOError:
                try:
                    config.load_incluster_config()  # How to set up the client from within a k8s pod
                except config.config_exception.ConfigException as error:
                    message = f"Could not configure kubernetes python client : {error}"
                    app.logger.error(message)
                    raise ExecutionEngineKuberneteError(message)

            api_instance = client.CoreV1Api(client.ApiClient())
            elapsed_time = time.time() - start_time
            app.logger.debug(f'K8 api config time : {elapsed_time}')

            start_time = time.time()
            resp = api_instance.create_namespaced_pod(body=k8_conf,
                                                      namespace=pod_namespace)
            elapsed_time = time.time() - start_time
            app.logger.debug(f'K8 api pod submission : {elapsed_time}')

            start_time = time.time()
            while True:
                resp = api_instance.read_namespaced_pod(name=pod_name,
                                                        namespace=pod_namespace)

                if resp.status.phase != 'Pending':
                    break
                time.sleep(1)
            elapsed_time = time.time() - start_time
            app.logger.debug(f'K8 api pod pending : {elapsed_time}')

            return pod_name

        else:
            pass  # launch exception

    else:
        pass  # launch exception


def kubernetes_service_generate(usecase, generation_id, user_id):

    # Retrieve the kubernetes configuration file regarding execution
    # engine block
    eeb_k8_filepath = Config().eeb_filepath

    if Path(eeb_k8_filepath).exists():

        app.logger.debug(f'pod configuration file found')

        k8_conf = None
        with open(eeb_k8_filepath) as f:
            k8_conf = yaml.safe_load(f)

        if k8_conf is not None:

            # Overload pod configuration file
            pod_name = f'generation{generation_id}-usr{user_id}-{uuid.uuid4()}'
            pod_namespace = k8_conf['metadata']['namespace']
            k8_conf['metadata']['name'] = pod_name
            k8_conf['spec']['containers'][0]['args'] = [
                '--generate', str(generation_id)]

            app.logger.debug(f'--------------------')
            app.logger.debug(f'pod settings : ')
            app.logger.debug(f'name : {pod_name}')
            app.logger.debug(f'generating reference : {usecase}')
            app.logger.debug(
                f'target image : {k8_conf["spec"]["containers"][0]["image"]}')

            start_time = time.time()
            # Create k8 api client object
            try:
                config.load_kube_config()
            except IOError:
                try:
                    config.load_incluster_config()  # How to set up the client from within a k8s pod
                except config.config_exception.ConfigException as error:
                    message = f"Could not configure kubernetes python client : {error}"
                    app.logger.error(message)
                    raise ExecutionEngineKuberneteError(message)

            api_instance = client.CoreV1Api(client.ApiClient())
            elapsed_time = time.time() - start_time
            app.logger.debug(f'K8 api config time : {elapsed_time}')

            start_time = time.time()
            resp = api_instance.create_namespaced_pod(body=k8_conf,
                                                      namespace=pod_namespace)
            elapsed_time = time.time() - start_time
            app.logger.debug(f'K8 api pod submission : {elapsed_time}')

            start_time = time.time()
            while True:
                resp = api_instance.read_namespaced_pod(name=pod_name,
                                                        namespace=pod_namespace)

                if resp.status.phase != 'Pending':
                    break
                time.sleep(1)
            elapsed_time = time.time() - start_time
            app.logger.debug(f'K8 api pod pending : {elapsed_time}')

            return pod_name

        else:
            pass  # launch exception

    else:
        pass  # launch exception


def kubernetes_service_allocate(pod_name):
    """
    Launch kubernetes service to build the study pod if the server_mode is Kubernetes

    :param study_case_identifier: study case identifier to allocate
    :type study_case_identifier: int
    :return: The state of the kubernetes services
    """
    # Create k8 api client object
    try:
        config.load_kube_config()
    except IOError:
        try:
            config.load_incluster_config()  # How to set up the client from within a k8s pod
        except config.config_exception.ConfigException as error:
            message = f"Could not configure kubernetes python client : {error}"
            app.logger.error(message)
            raise ExecutionEngineKuberneteError(message)
    core_api_instance = client.CoreV1Api(client.ApiClient())
    apps_api_instance = client.AppsV1Api(client.ApiClient())

    kubernetes_study_server_service_create(pod_name, core_api_instance)
    kubernetes_study_server_deployment_create(pod_name, core_api_instance, apps_api_instance)



def kubernetes_study_server_service_create(pod_name, core_api_instance):
    service_k8_filepath = Config().service_study_server_filepath

    k8_service = None
    with open(service_k8_filepath) as f:
        k8_service_tplt = Template(f.read())
        k8_service_tplt = k8_service_tplt.render( pod_name=pod_name)
        k8_service = yaml.safe_load(k8_service_tplt)
    namespace = k8_service['metadata']['namespace']

    # check service existance
    service_found = False
    try:
        resp = core_api_instance.read_namespaced_service(name=pod_name, namespace=namespace)
        service_found = True
        print(f'Check: {resp}')
    except client.rest.ApiException as api_exception:
        if api_exception.status == 404:
            print(f'Not found')
        else:
            raise api_exception

    # create service
    if not service_found:
        resp = core_api_instance.create_namespaced_service(body=k8_service, namespace=namespace)
        print(resp)
        # wait while service is created
        count = 0
        while count < 60:
            try:
                service = core_api_instance.read_namespaced_service_status(name=pod_name, namespace=namespace)
                print(service)
                break
            except client.rest.ApiException as api_exception:
                if api_exception.status == 404:
                    print(f'Not found')
                else:
                    raise api_exception
            #if service.status.phase != 'Pending':
            #        break
            time.sleep(10)
            count += 1
    else:
        print('service already exist')



def kubernetes_study_server_deployment_create(pod_name, core_api_instance, apps_api_instance):
    deployment_k8_filepath = Config().deployment_study_server_filepath

    k8_deploy = None
    with open(deployment_k8_filepath) as f:
        k8_deploy_tplt = Template(f.read())
        k8_deploy_tplt = k8_deploy_tplt.render(pod_name=pod_name)
        k8_deploy = yaml.safe_load(k8_deploy_tplt)
    namespace = k8_deploy['metadata']['namespace']

    # check deployment existance
    deployement_found = False
    try:
        dplmt = apps_api_instance.read_namespaced_deployment(name=pod_name, namespace=namespace)
        deployement_found = True
    except client.rest.ApiException as api_exception:
        if api_exception.status == 404:
            print(f'Not found')
        else:
            raise api_exception

    # create deployment
    if not deployement_found:
        resp = apps_api_instance.create_namespaced_deployment(body=k8_deploy, namespace=namespace)
        print(resp)
        # wait while deployment is created
        count = 0
        while count < 60:
            try:
                resp = apps_api_instance.read_namespaced_deployment_status(name=pod_name, namespace=namespace)
                print(resp.status)
                break
            except client.rest.ApiException as api_exception:
                if api_exception.status == 404:
                    print(f'Not found')
                else:
                    raise api_exception
            time.sleep(10)
            count += 1
    else:
        print('deployement already exist')

    #check pod created
    pod_status = ""
    count = 0
    while count < 60:
        pod_list = core_api_instance.list_namespaced_pod(namespace=namespace)

        for pod in pod_list.items:
            if pod.metadata.name.startswith(f"{pod_name}-"):
                pod_status = pod.status.phase
                break
        if pod_status == "Running":
            break

        time.sleep(10)
        count += 1
    if pod_status != "Running":
        raise ExecutionEngineKuberneteError("Pod not starting")



def kubernetes_service_delete(pod_name):

    # Retrieve the kubernetes configuration file regarding execution
    # engine block
    eeb_k8_filepath = Config().eeb_filepath

    if Path(eeb_k8_filepath).exists() and len(pod_name) > 0:

        app.logger.info(f'pod configuration file found')

        k8_conf = None
        with open(eeb_k8_filepath) as f:
            k8_conf = yaml.safe_load(f)

        if k8_conf is not None:

            # Retrieve pod configuration
            pod_namespace = k8_conf['metadata']['namespace']

            # Create k8 api client object
            try:
                config.load_kube_config()
            except IOError:
                try:
                    config.load_incluster_config()  # How to set up the client from within a k8s pod
                except config.config_exception.ConfigException as error:
                    message = f"Could not configure kubernetes python client : {error}"
                    app.logger.error(message)
                    raise ExecutionEngineKuberneteError(message)

            api_instance = client.CoreV1Api(client.ApiClient())

            resp = api_instance.delete_namespaced_pod(name=pod_name, namespace=pod_namespace)
            app.logger.info(f'k8s response : {resp}')

        else:
            message = f"Pod configuration not loaded or empty pod configuration"
            app.logger.error(message)
            raise ExecutionEngineKuberneteError(message)

    else:
        if not Path(eeb_k8_filepath).exists():
            message = f"Missing SoSTrades pod configuration file in: {eeb_k8_filepath}"
        else:# not pod name
            message = f"Missing SoSTrades pod name: {pod_name}"
        app.logger.error(message)
        raise ExecutionEngineKuberneteError(message)

def kubernetes_eeb_service_pods_status(pod_identifiers):

    result = {}

    # Retrieve the kubernetes configuration file regarding execution
    # engine block
    eeb_k8_filepath = Config().eeb_filepath

    if Path(eeb_k8_filepath).exists():

        app.logger.debug(f'pod configuration file found')

        k8_conf = None
        with open(eeb_k8_filepath) as f:
            k8_conf = yaml.safe_load(f)

        if k8_conf is not None:

            # Retrieve pod configuration
            pod_namespace = k8_conf['metadata']['namespace']
            result = kubernetes_service_pods_status(pod_identifiers, pod_namespace)

        else:
            pass  # launch exception

    else:
        pass  # launch exception

    return result

def kubernetes_study_service_pods_status(pod_identifiers):

    result = None

    # Retrieve the kubernetes configuration file regarding execution
    # engine block
    study_k8_filepath = Config().service_study_server_filepath

    if Path(study_k8_filepath).exists() and pod_identifiers is not None:

        app.logger.debug(f'pod configuration file found')

        k8_conf = None
        with open(study_k8_filepath) as f:
            yaml_content = Template(f.read())
            yaml_content = yaml_content.render(service_name="svc", pod_name=pod_identifiers)
            k8_conf = yaml.safe_load(yaml_content)
        if k8_conf is not None:

            # Retrieve pod configuration
            pod_namespace = k8_conf['metadata']['namespace']
            result = kubernetes_service_pods_status(pod_identifiers, pod_namespace, False)
            if len(result) > 0:
                status = list(result.values())[0]

                if status == "Running":
                    result = "IN_PROGRESS"
                    # the pod is running, we have to send a ping to the api to check that it is running too
                    port = k8_conf['spec']['ports'][0]["port"]
                    study_server_url = f"https://{pod_identifiers}.{pod_namespace}.svc.cluster.local:{port}/api/ping"
                    ssl_path = app.config['INTERNAL_SSL_CERTIFICATE']
                    study_response_data = ""
                    try:
                        resp = requests.request(
                            method='GET', url=study_server_url, verify=ssl_path
                        )
                        app.logger.info(f'request pod {pod_identifiers}:{resp}')

                        if resp.status_code == 200:
                            study_response_data = resp.json()

                    except:
                        app.logger.exception('An exception occurs when trying to reach study server')

                    if study_response_data == "pong":
                        result = "DONE"

        else:
            pass  # launch exception

    else:
        pass  # launch exception

    return result



def kubernetes_service_pods_status(pod_identifiers, pod_namespace, is_pod_name_complete=True):
    '''
    check pod status
    :param pod_identifiers: list of pod names or the pod_name
    :param pod_namespace: namespace k8 where to find the pod
    :param is_pod_name_complete: boolean to test if the pod name is exactly the pod name or just the begining of the name
    in this case pod_identifiers is a pod_name
    '''
    result = {}

    # Create k8 api client object
    try:
        config.load_kube_config()
    except IOError:
        try:
            config.load_incluster_config()  # How to set up the client from within a k8s pod
        except config.config_exception.ConfigException as error:
            message = f"Could not configure kubernetes python client : {error}"
            app.logger.error(message)
            raise ExecutionEngineKuberneteError(message)

    api_instance = client.CoreV1Api(client.ApiClient())

    pod_list = api_instance.list_namespaced_pod(
        namespace=pod_namespace)

    for pod in pod_list.items:

        if pod.metadata.name in pod_identifiers:
            result.update({pod.metadata.name: pod.status.phase})
            break
        elif not is_pod_name_complete:
            # check pod name start with study-server-id- (the "-" is to prevent amalgame with study-server ids
            if pod.metadata.name.startswith(f"{pod_identifiers}-"):
                result.update({pod.metadata.name: pod.status.phase})
                break
    return result


def kubernetes_get_pod_info(pod_name):
    """
    Delete a previously created pod in kubernetes
    :param pod_name: unique name of the pod => metadata.name
    :return: dict with cpu usage (number of cpu) and memory usage (Go)
    """

    result = {
        'cpu': '----',
        'memory': '----'
    }

    # Retrieve the kubernetes configuration file regarding execution
    # engine block
    eeb_k8_filepath = Config().eeb_filepath

    if Path(eeb_k8_filepath).exists():

        app.logger.debug(f'pod configuration file found')

        k8_conf = None
        with open(eeb_k8_filepath) as f:
            k8_conf = yaml.safe_load(f)

        if k8_conf is not None:

            # Retrieve pod configuration
            pod_namespace = k8_conf['metadata']['namespace']

            # Create k8 api client object
            try:
                config.load_kube_config()
            except IOError:
                try:
                    config.load_incluster_config()  # How to set up the client from within a k8s pod
                except config.config_exception.ConfigException as error:
                    message = f"Could not configure kubernetes python client : {error}"
                    app.logger.error(message)
                    raise ExecutionEngineKuberneteError(message)

            try:
                api = client.CustomObjectsApi()
                resources = api.list_namespaced_custom_object(group="metrics.k8s.io", version="v1beta1",
                                                              namespace=pod_namespace, plural="pods")

                pod_searched = list(filter(lambda pod: pod['metadata']['name'] == pod_name, resources['items']))

                pod_cpu = round(float(''.join(
                    filter(str.isdigit, pod_searched[0]['containers'][0]['usage']['cpu']))) / 1e9, 2)
                pod_memory = round(float(''.join(
                    filter(str.isdigit, pod_searched[0]['containers'][0]['usage']['memory']))) / (1024 * 1024), 2)
                result['cpu'] = f'{pod_cpu} [-]'
                result['memory'] = f'{pod_memory} [Go]'

            except Exception as error:
                message = f"Unable to retrieve pod metrics: {error}"
                app.logger.error(message)
                raise ExecutionEngineKuberneteError(message)
        else:
            message = f"Error loading Kubernetes configuration"
            app.logger.error(message)
            raise ExecutionEngineKuberneteError(message)
    else:
        message = f"Unable to retrieve Kubernetes configuration file at path: {eeb_k8_filepath}"
        app.logger.error(message)
        raise ExecutionEngineKuberneteError(message)

    return result

def kubernetes_service_delete_study_server(pod_identifiers):

    # Retrieve the kubernetes configuration file regarding execution
    # engine block
    study_k8_filepath = Config().service_study_server_filepath

    if Path(study_k8_filepath).exists() and pod_identifiers is not None:

        app.logger.debug(f'pod configuration file found')

        k8_conf = None
        with open(study_k8_filepath) as f:
            yaml_content = Template(f.read())
            yaml_content = yaml_content.render(service_name="svc", pod_name=pod_identifiers)
            k8_conf = yaml.safe_load(yaml_content)
        if k8_conf is not None:
            # Retrieve pod configuration
            pod_namespace = k8_conf['metadata']['namespace']

            # Create k8 api client object
            try:
                config.load_kube_config()
            except IOError:
                try:
                    config.load_incluster_config()  # How to set up the client from within a k8s pod
                except config.config_exception.ConfigException as error:
                    message = f"Could not configure kubernetes python client : {error}"
                    app.logger.error(message)
                    raise ExecutionEngineKuberneteError(message)

            core_api_instance = client.CoreV1Api(client.ApiClient())
            apps_api_instance = client.AppsV1Api(client.ApiClient())

            # check service existance
            service_found = False
            try:
                resp = core_api_instance.read_namespaced_service(name=pod_identifiers, namespace=pod_namespace)
                service_found = True
            except client.rest.ApiException as api_exception:
                if api_exception.status == 404:
                    print(f'Not found')
            # delete service
            if service_found:
                try:
                    resp = core_api_instance.delete_namespaced_service(name=pod_identifiers, namespace=pod_namespace)
                    if resp.status != "Success":
                        app.logger.error(f'The deletion of the service named {pod_identifiers} has not succeeded' )
                    else:
                        app.logger.info(f"service {pod_identifiers} has been successfully deleted")
                except Exception as api_exception:
                    app.logger.error(api_exception)

            # check deployment existance
            deployement_found = False
            try:
                dplmt = apps_api_instance.read_namespaced_deployment(name=pod_identifiers, namespace=pod_namespace)
                deployement_found = True
            except client.rest.ApiException as api_exception:
                if api_exception.status == 404:
                    print(f'Not found')
            # delete deployment
            if deployement_found:
                try:
                    resp = apps_api_instance.delete_namespaced_deployment(name=pod_identifiers, namespace=pod_namespace)
                    if resp.status != "Success":
                        app.logger.error(f'The deletion of the deployment named {pod_identifiers} has not succeeded' )
                    else:
                        app.logger.info(f"Deployment {pod_identifiers} has been successfully deleted")
                except Exception as api_exception:
                    app.logger.error(api_exception)
        else:
            message = f"Pod configuration not loaded or empty pod configuration"
            app.logger.error(message)
            raise ExecutionEngineKuberneteError(message)
