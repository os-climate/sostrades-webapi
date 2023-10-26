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
various function useful to python coding
"""

import logging
from os import SEEK_END
import ast
from time import time
from typing import Optional
import numpy as np
from io import StringIO
from sos_trades_api.server.base_server import app


def isevaluatable(s):
    """
    Check if string only contains a literal of type - strings, numbers, tuples, lists, dicts, booleans, and None
    :param s:
    :return:
    """
    try:
        return ast.literal_eval(s)
    except (ValueError, SyntaxError) as e:
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
    except Exception as e:
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

    # List of lines returned to caller
    result = []
    app.logger.info(f"Opening log file {file_name}.")

    # Add monitoring of time spent on some lines
    time_spent_read = 0
    time_spent_seek = 0

    # Open file for reading in binary mode
    with open(file_name, 'rb') as file_object:
        app.logger.info(f"Log file opened {file_name}.")
        # Set file pointer to the end and initialize pointer value
        file_object.seek(0, SEEK_END)
        pointer_location = file_object.tell()

        # Boolean to drive the loop
        stop = False
        while not stop:

            # If we reach the beginning of the file, then  stop the loop
            if pointer_location < 0:
                stop = True
            # If we have stored all the needed lines
            elif len(result) == line_count:
                stop = True
            else:
                start_ts = time.time()
                # Set file object to the location of the pointer
                file_object.seek(pointer_location)

                # Diagnosis : monitor time spent
                time_spent_seek += time() - start_ts
                start_ts = time.time()
                # Read current character
                read_byte = file_object.read(1)
                time_spent_read += time() - start_ts

                # Check if read character is a carriage return
                if read_byte == b'\n':

                    # Check if line contain any characters
                    decoded_buffer = binary_buffer.decode(encoding=encoding, errors="ignore")
                    if len(decoded_buffer.strip()) != 0:
                        # We achieve to find the beginning of the line, so we can store it in the result
                        result.append(decoded_buffer[::-1])

                    # Reset binary buffer
                    binary_buffer = bytearray()
                else:
                    # If last read character is not eol then add it in buffer
                    binary_buffer.extend(read_byte)

                # Shift the pointer to the previous location
                # (for the next loop)
                pointer_location -= 1

        # This case occurs if we reach the beginning of the file before having read all the requested lines
        # So save the last store line
        if len(binary_buffer) > 0:
            result.append(binary_buffer.decode(encoding=encoding, errors="ignore")[::-1])
            
    app.logger.info(f"Done parsing logs {file_name}. Time spent reading : {time_spent_read}s. Time spent seeking : {time_spent_seek}s.")
    # Reverse the list before returning
    return list(reversed(result))
