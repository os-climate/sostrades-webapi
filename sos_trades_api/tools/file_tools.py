'''
Copyright 2022 Airbus SAS
Modifications on 2024/06/07 Copyright 2024 Capgemini
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
import time
from datetime import datetime

from sos_trades_api.models.custom_json_encoder import CustomJsonEncoder
from sos_trades_api.tools.code_tools import convert_byte_into_byte_unit_targeted

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

        with open(file_path, "w+") as json_file:
            json.dump(object_to_write, json_file, cls=CustomJsonEncoder)
            saved = True

    return saved

def read_object_in_json_file(file_path):
    """
    Retrieve object from json file
    """
    result = None
    if os.path.exists(file_path):
        with open(file_path) as json_file:
            result = json.load(json_file)

    return result


def get_metric_from_file_system(memory_file_path: str, cpu_file_path: str, unit_byte_to_conversion: str) -> tuple:
    """
    :Summary:
        Retrieves memory and CPU metrics from the file system and converts them to the specified unit.

    :Args:
        memory_file_path (str): The file path to the memory stat file.
        cpu_file_path (str): The file path to the CPU stat file.
        unit_byte_to_conversion (str): The target unit for memory conversion.

    :Returns:
        tuple: A tuple containing the converted memory usage and the CPU usage percentage.

    """
    if not memory_file_path or not memory_file_path.strip():
        raise ValueError("The memory file path cannot be none or empty.")
    if not cpu_file_path or not cpu_file_path.strip():
        raise ValueError("The CPU file path cannot be none or empty.")
    if not unit_byte_to_conversion or not unit_byte_to_conversion.strip():
        raise ValueError("The unit for memory conversion cannot be none or empty.")

    # Retrieve CPU usage from file system
    # First measurement
    start_time = datetime.now()
    start_usage_usec = get_cpu_usage_from_file(cpu_file_path)

    # Sleep for a short period
    time.sleep(0.5)

    # Second measurement
    end_time = datetime.now()
    end_usage_usec = get_cpu_usage_from_file(cpu_file_path)

    # Calculate elapsed time in seconds
    elapsed_time_sec = (end_time - start_time).total_seconds()

    # Calculate CPU usage in seconds
    cpu_usage_seconds = (end_usage_usec - start_usage_usec) / 1e6

    # Calculate CPU usage percentage
    cpu_usage = (cpu_usage_seconds / elapsed_time_sec) * 100

    # Retrieve memory from file system
    memory_lines = get_lines_from_file(memory_file_path)
    if not memory_lines or not memory_lines[0].strip():
        raise FileExistsError(f"The file '{memory_file_path}' is empty or invalid.")

    bytes_value = int(memory_lines[0])
    memory_converted = convert_byte_into_byte_unit_targeted(bytes_value, "byte", unit_byte_to_conversion)

    return round(memory_converted, 2), round(cpu_usage, 2)


def get_lines_from_file(file_path: str) -> list:
    """
       :Summary:
           Open a file and return its lines.

       :Args:
           file_path (str): Path of file

       :Return: Lines of this file.
           :rtype: list
       """
    if file_path is not None and len(file_path.strip()) > 0:
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                lines = file.readlines()
                if len(lines) > 0:
                    return lines
                else:
                    raise FileExistsError(f"The file '{file_path}' is empty.")
        else:
            FileNotFoundError(f"The file '{file_path}' not found.")
    else:
        raise ValueError("The path cannot be none or empty.")


def get_cpu_usage_from_file(cpu_stat_path: str):
    """
        :Summary:
           Reads the CPU usage statistics from the specified cgroup CPU stat file.
           This function opens the given file, reads its content, and extracts the
           'usage_usec' value which represents the total CPU time consumed by tasks
           in this cgroup in microseconds.

       :Args:
           cpu_stat_path (str): The file path to the cgroup CPU stat file.

       :Returns:
           int: The total CPU usage in microseconds.

       """
    cpu_line = get_lines_from_file(cpu_stat_path)
    cpu_stat = {}
    for line in cpu_line:
        key, value = line.split()
        cpu_stat[key] = int(value)
    return cpu_stat['usage_usec']


