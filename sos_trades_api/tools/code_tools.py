'''
Copyright 2022 Airbus SAS
Modifications on 2023/09/14-2024/05/07 Copyright 2023 Capgemini

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

import logging
import os
import re
from time import time
from typing import Optional

from sos_trades_api.server.base_server import app

"""
various function useful to python coding
"""

def time_function(logger: Optional[logging.Logger] = None):
    """
    This decorator times another function and logs time spend in logger given as argument (if any)
    """

    def inner(func):
        def wrapper_function(*args, **kwargs):
            """Fonction wrapper"""
            t_start = time()
            return_args = func(*args, **kwargs)
            t_end = time()
            execution_time = t_end - t_start
            if logger is not None:
                logger.info(f"Execution time {func.__name__}: {execution_time:.4f}s")
            else:
                print(f"Execution time {func.__name__}: {execution_time:.4f}s")
            return return_args

        return wrapper_function

    return inner

@time_function(logger=app.logger)
def file_tail(file_name, line_count, encoding="utf-8"):
    """
    Open a file and return the {{line_count}} last line
    Code use file pointer location to  avoid to read the entire file

    :param file_name: file path of the file to read
    :type str

    :param line_count: number of line to read
    :type integer

    :param encoding: encoding to use
    :type str

    :return: list of string
    """
    # Temporary buffer to store read lines during process
    binary_buffer = bytearray()
    buffer_size = 4096

    app.logger.debug(f"Opening log file {file_name}.")

    # Open file for reading in binary mode
    with open(file_name, "rb") as file_object:
        app.logger.debug(f"Log file opened {file_name}.")
        # Set file pointer to the end and initialize pointer value
        file_object.seek(0, os.SEEK_END)
        file_size = file_object.tell()
        read_size = 0

        # keep track of previous iteration read bytes, to reduce seek function calls
        previous_n_read_bytes = 0

        # While we haven't read enough lines, or reached the end of the file
        while binary_buffer.count(b"\n") < line_count and read_size < file_size:
            # Amount of bytes to read
            n_bytes_to_read = min(buffer_size, file_size - read_size)

            # Seek position from current position
            offset_from_current_pos = -(n_bytes_to_read + previous_n_read_bytes)
            file_object.seek(offset_from_current_pos, os.SEEK_CUR)

            # Read bytes
            read_bytes = file_object.read(n_bytes_to_read)
            read_size += n_bytes_to_read

            # Replace pointer
            binary_buffer.extend(read_bytes[::-1])

            # Keep track of bytes read this iteration
            previous_n_read_bytes = n_bytes_to_read

    # Decode buffer
    content = binary_buffer[::-1].decode(encoding=encoding, errors="ignore")

    # Split lines
    lines = content.split("\n")
    if len(lines) > line_count:
        # Trim aditionnal lines
        lines = lines[-line_count:]

    app.logger.debug(f"Done parsing logs {file_name}.")
    return lines


def convert_byte_into_byte_unit_targeted(bytes_to_convert: float, unit_source: str, unit_bytes: str) -> float:
    """
    :Summary:
        Convert a given amount of bits into bytes based on specified units.

    :Args:
        bytes_to_convert (float): The amount of bytes to convert.
        unit_source (str): The unit of source bytes.
        unit_bytes (str): The unit to convert bytes.

    :Return: The converted value in bytes.
        :rtype: float
    """

    byte_converted = None

    # Conversion factors
    bytes_to_megabyte = 1 / (1024 * 1024)
    bytes_to_gigabyte = 1 / (1024 * 1024 * 1024)
    kibibytes_to_megabytes = 1024/1000/1000
    kibibytes_to_gigabytes = 1024/1000/1000/1000
    mebibytes_to_megabytes = 1024*1024/1000/1000
    mebibytes_to_gigabytes = 1024*1024/1000/1000/1000
    gibibytes_to_gigabytes = 1024*1024*1024/1000/1000/1000

    if unit_source.lower() == "byte":
        # Convert byte to Megabyte
        if unit_bytes.lower() == "mb" or unit_bytes.lower() == "megabyte":
            byte_converted = bytes_to_convert * bytes_to_megabyte

        # Convert v to Gigabyte
        elif unit_bytes.lower() == "gb" or unit_bytes.lower() == "gigabyte":
            byte_converted = bytes_to_convert * bytes_to_gigabyte
        else:
            raise ValueError(f'Unit {unit_bytes} is not handled')

    elif unit_source.lower() == "ki" or unit_source.lower() == "kibibyte":
        # Convert kibibyte to Megabyte
        if unit_bytes.lower() == "mb" or unit_bytes.lower() == "megabyte":
            byte_converted = bytes_to_convert * kibibytes_to_megabytes

        # Convert kibibyte to Gigabyte
        elif unit_bytes.lower() == "gb" or unit_bytes.lower() == "gigabyte":
            byte_converted = bytes_to_convert * kibibytes_to_gigabytes
        else:
            raise ValueError(f'Unit {unit_bytes} is not handled')

    elif unit_source.lower() == "mi" or unit_source.lower() == "mebibyte":

        # Convert Megabyte to Megabyte
        if unit_bytes.lower() == "mb" or unit_bytes.lower() == "megabyte":
            byte_converted = bytes_to_convert * mebibytes_to_megabytes

        # Convert Megabyte to Gigabyte
        elif unit_bytes == "gb" or unit_bytes.lower() == "gigabyte":
            byte_converted = bytes_to_convert * mebibytes_to_gigabytes
        else:
            raise ValueError(f'Unit {unit_bytes} is not handled')

    elif unit_source.lower() == "gi" or unit_source.lower() == "gibibyte":

        # Convert Gigabyte to Gigabyte
        if unit_bytes.lower() == "gb" or unit_bytes.lower() == "gigabyte":
            byte_converted = bytes_to_convert * gibibytes_to_gigabytes
        else:
            raise ValueError(f'Unit {unit_bytes} is not handled')


    else:
        raise ValueError(f'Unit {unit_source} is not handled')

    return byte_converted


def extract_number_and_unit(input_string: str) -> tuple:
    """
    :Summary:
        Extracts the number and unit from a given string.

    Args:
        input_string (str): The string from which to extract the number.

    :Return: A tuple containing the number and the unit.
        :rtype: tuple (number: int, unit: str)
    """

    # Use a regular expression to extract the number and the unit
    match = re.match(r"(\d+[\.,]?\d*)\s*([a-zA-Z]+)", input_string.strip())
    if not match:
        raise ValueError("The input string must contain both a number and a unit.")

    # Replace comma with a dot to handle decimal numbers correctly
    number = float(match.group(1).replace(',', '.'))
    unit = match.group(2)

    return number, unit

