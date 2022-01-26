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

from os import SEEK_END
import ast

def isevaluatable(s):
    """
    Check if string only contains a literal of type - strings, numbers, tuples, lists, dicts, booleans, and None
    :param s:
    :return:
    """
    try:
        return ast.literal_eval(s)
    except (ValueError, SyntaxError) as e:
        return s


def file_tail(file_name, line_count):
    """
    Open a file and return the {{line_count}} last line
    Code use file pointer location to  avoid to read the entire file

    :param file_name: file path of the file to read
    :type str

    :param line_count: number of line to read
    :type integer

    :return: list of string
    """

    # Temporary buffer to store read lines during process
    binary_buffer = bytearray()

    # List of lines returned to caller
    result = []

    # Open file for reading in binary mode
    with open(file_name, 'rb') as file_object:

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
                # Set file object to the location of the pointer
                file_object.seek(pointer_location)

                # Read current character
                read_byte = file_object.read(1)

                # Check if read character is a carriage return
                if read_byte == b'\n':

                    # We achieve to find the beginning of the line, so we can store it in the result
                    result.append(binary_buffer.decode()[::-1])

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
            result.append(binary_buffer.decode()[::-1])

    # Reverse the list before returning
    return list(reversed(result))
