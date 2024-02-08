'''
Copyright 2022 Airbus SAS
Modifications on 2023/09/14-2023/11/23 Copyright 2023 Capgemini

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
various function useful to python coding
"""

import logging
import os
import ast
from time import time
from typing import Optional
import numpy as np
from sos_trades_api.server.base_server import app


def isevaluatable(s):
    """
    Check if string only contains a literal of type - strings, numbers, tuples, lists, dicts, booleans, and None
    :param s:
    :return:
    """
    try:
        return ast.literal_eval(s)
    except (ValueError, SyntaxError):
        # deal with numpy arrays that have the numpy format (convert it to list then to array)
        if isinstance(s, str) and s.startswith('[') and s.endswith(']'):
            return evaluate_arrays(s)
        return s      

def evaluate_arrays(input_str):
    """
    convert a string into an array or a list of array 
    :param input_str: the string to convert into an array
    :type string
    :return: the numpy array
    """
    #fix the \n and , if needed and split by ' '
    array_content = input_str.replace('array(','').replace(')','').replace('\n',' ').replace(',',' ').split(' ')
    # remove empty entry
    array_content = [x for x in array_content if x != '']
    # check bracket alone (when there is a space between bracket and digit '[ 1 2 ]' 
    # we need to remove the bracket alone and add it to the next digit)
    for i in range(0,len(array_content)):
        if array_content[i] == '[' and i+1 < len(array_content):
            array_content[i+1] = '[' + array_content[i+1]
        if array_content[i] == ']' and i-1 >= 0:
            array_content[i-1] =  array_content[i-1] + ']'
    array_content = [x for x in array_content if x != '[' and x != ']']
    # recreate the string list that can be interpreted as a list
    new_s = ','.join(array_content)
    try:
        # convert the string in list then in arrays
        eval = convert_list_to_arrays(ast.literal_eval(new_s))
        # the writing of an array into a list if array() instead of [x y] 
        if 'array(' in input_str:
            return list(eval)
        else:
            return eval
    except Exception:
        return input_str
    

def convert_list_to_arrays(input_list):
    """
    convert a list into an array and if the list contains list, convert into array of arrays
    :param input_list: the list to convert into an array
    :type list
    :return: the list converted into numpy array
    """
    if isinstance(input_list, list):
        # Si la liste contient d'autres listes, récursion
        return np.array([convert_list_to_arrays(item) for item in input_list])
    else:
        # Si l'élément est un nombre return the element
        return input_list


def time_function(logger: Optional[logging.Logger] = None):
    """
    This decorator times another function and logs time spend in logger given as argument (if any)
    """

    def inner(func):
        def wrapper_function(*args, **kwargs):
            """fonction wrapper"""
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
    with open(file_name, 'rb') as file_object:
        app.logger.debug(f"Log file opened {file_name}.")
        # Set file pointer to the end and initialize pointer value
        file_object.seek(0, os.SEEK_END)
        file_size = file_object.tell()
        read_size = 0

        # keep track of previous iteration read bytes, to reduce seek function calls
        previous_n_read_bytes = 0

        # While we haven't read enough lines, or reached the end of the file
        while binary_buffer.count(b'\n') < line_count and read_size < file_size:
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
    lines = content.split('\n')
    if len(lines) > line_count:
        # Trim aditionnal lines
        lines = lines[-line_count:]
    
    app.logger.debug(f"Done parsing logs {file_name}.")
    return lines
