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
Random password generator
"""

import random
import string


class InvalidPassword(Exception):
    """Password Exception"""

    def __init__(self):

        msg = '''\
            Given password is invalid. Password must fulfilled the following policies
            - ascii lower case (1 minimum)
            - ascii upper case (1 minimum)
            - all digits numbers (1 minimum)
            - punctuation characters (1 minimum) => !"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~
            '''

        Exception.__init__(self, msg)

def generate_password(length=8):
    """ Generate a random password regarding the length parameter given as attribute
        Generated password is a random combination of:
        - ascii lower case (1 minimum)
        - ascci upper case (1 minimum)
        - all digits numbers (1 minimum)
        - punctuation characters (1 minimum) => !"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~

        :param length: number of character for the password to generate (default 8, min 8)
        :type int

        :param str, generated password
    """

    if length < 8:
        length = 8

    # Store all characters use to build password
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    num = string.digits
    symbols = string.punctuation

    # Put them in the same list
    all_characters = lower + upper + num + symbols

    password_ok = False

    while not password_ok:

        # Randomize character selection in the list
        password_as_list = random.sample(all_characters, length)

        # set result list to string
        password = ''.join(password_as_list)

        # Check password content
        password_ok = check_password(password)

    return password


def check_password(password):
    """ Check if password is compliant with the policy (see generate_password function)

        :param password: number of character for the password to generate (default 8, min 8)
        :type str

        :return boolean, True if the password is compliant with the policy
    """

    # character to check
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    num = string.digits
    symbols = string.punctuation

    count_lower = len(set(password).intersection(lower))
    count_upper = len(set(password).intersection(upper))
    count_num = len(set(password).intersection(num))
    count_symbols = len(set(password).intersection(symbols))

    return count_lower >= 1 and count_upper >= 1 and count_num >= 1 and count_symbols >= 1


if __name__ == "__main__":

    pwd = generate_password(20)

    print(pwd)
