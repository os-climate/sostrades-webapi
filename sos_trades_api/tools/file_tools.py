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
import json
import os

from sos_trades_api.models.custom_json_encoder import CustomJsonEncoder

"""
mode: python; py-indent-offset: 4; tab-width: 4; coding: utf-8
various function  regarding file api
"""

# pylint: disable=line-too-long

def write_object_in_json_file(object_to_write, file_path):
    """
    Write data into a json file at the given filePath (existing or not)
    :param object_to_write: data to write into the file
    :type object_to_write: any
    """
    saved = False
    if object_to_write is not None:

        with open(file_path, 'w+') as json_file:
            json.dump(object_to_write, json_file, cls=CustomJsonEncoder)
            saved = True

    return saved

def read_object_in_json_file(file_path):
    """
    Retrieve object from json file
    """
    result = None
    if os.path.exists(file_path):
        with open(file_path, 'r') as json_file:
            result = json.load(json_file)

    return result




