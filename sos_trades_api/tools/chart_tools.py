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

import time

from sostrades_core.tools.post_processing.post_processing_factory import (
    PostProcessingFactory,
)

"""
various function  regarding chart api
"""


def load_post_processing(exec_engine, with_charts):
    """Methods that iterates through all execution engine disciplines to request their associated filter

    :params: exec_engine execution engine to request
    :type: ExecutionEngine

    :params: with_charts associated chart will be generated
    :type: boolean

    :return: dictionary with discipline id as key and ChartFilter list as value and a second dictionary depending of the 'with_chart' arguments with discipline id as key and Chart list as value
    """

    all_post_processings = {}

    if exec_engine is not None and exec_engine.dm is not None and exec_engine.dm.disciplines_dict is not None and len(exec_engine.dm.disciplines_dict) > 0:
        start_time = time.time()
        exec_engine.logger.info(
            f'Retrieve post-processing for study ({len(exec_engine.dm.disciplines_dict)} discipline to check) ')

        post_processing_factory = PostProcessingFactory()

        all_post_processings = post_processing_factory.get_all_post_processings(
            exec_engine, not with_charts)

        exec_engine.logger.info(
            f'End of post-processing generation ({time.time() - start_time} seconds)')

    return all_post_processings
