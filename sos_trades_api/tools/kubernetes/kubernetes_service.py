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
"""
mode: python; py-indent-offset: 4; tab-width: 4; coding: utf-8
Execution engine kubernete
"""
from kubernetes import client, config
from sos_trades_api.config import Config
from sos_trades_api.base_server import app
from os.path import join
from pathlib import Path
import uuid
import yaml
import time


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


def kubernetes_service_pods_status(pod_identifiers):

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

        else:
            pass  # launch exception

    else:
        pass  # launch exception

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
