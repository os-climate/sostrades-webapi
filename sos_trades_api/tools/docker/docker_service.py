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
"""
mode: python; py-indent-offset: 4; tab-width: 4; coding: utf-8
Execution engine kubernete
"""
from dockers import client
from sos_trades_api.config import Config
from sos_trades_api.server.base_server import app
from jinja2 import Template
from pathlib import Path
import uuid
import yaml
import time
import requests


class ExecutionEngineDockerError(Exception):
    """Base StudyCase Exception"""

    def __init__(self, msg=None):
        Exception.__init__(self, msg)

    def __str__(self):
        return self.__class__.__name__ + '(' + Exception.__str__(self) + ')'


def docker_container_allocate(pod_name):
    """
    Launch docker container 

    :param study_case_identifier: study case identifier to allocate
    :type study_case_identifier: int
    :return: The state of the container
    """
    #TODO
    pass


def docker_container_create(pod_name):
    pass


def docker_container_delete(pod_name):
    #TODO
    pass

def docker_container_status(pod_identifiers):

    result = {}

    # Retrieve the kubernetes configuration file regarding execution
    # engine block
    #TODO

    return result

