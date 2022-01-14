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
Execution engine kubernetes
"""
import threading
from sos_trades_api.tools.kubernetes.kubernetes_service import kubernetes_service_run, kubernetes_service_delete, \
    kubernetes_service_pods_status


class ExecutionEngineKubernetes:
    """
    Class that manage high level entries for kubernetes feature
    """

    def run(self, study, log_file_path):
        """
        Run a new pod into kubernetes

        :param study: study object to run
        :param log_file_path: file to redirect stdout and stderr
        :return: kubbernetes pod name
        """
        return kubernetes_service_run(study, log_file_path)

    def delete(self, pod_identifier):
        """
        Delete a previously created pod in kubernetes
        :param pod_identifier: name of the pod to delete
        :return: None
        """

        threading.Thread(
            target=kubernetes_service_delete,
            args=(pod_identifier, )).start()

    def pods_status(self, pod_identifiers):
        """

        :param pod_identifiers: list of pod identifier (name) to check status
        :return: dictionary with identifier as key and status as value
        """
        return kubernetes_service_pods_status(pod_identifiers)
