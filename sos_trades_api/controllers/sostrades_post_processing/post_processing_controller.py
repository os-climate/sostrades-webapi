'''
Copyright 2022 Airbus SAS
Modifications on 2023/11/23 Copyright 2023 Capgemini

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
from memory_profiler import profile
import tracemalloc
from sostrades_core.execution_engine.execution_engine import display_top

from sos_trades_api.server.base_server import study_case_cache
from sostrades_core.tools.post_processing.post_processing_factory import PostProcessingFactory
from sos_trades_api.controllers.sostrades_main.study_case_controller import light_load_study_case


class PostProcessingError(Exception):
    """Base StudyCase Exception"""

    def __init__(self, msg=None):
        Exception.__init__(self, msg)

    def __str__(self):
        return self.__class__.__name__ + '(' + Exception.__str__(self) + ')'

@profile
def load_post_processing(study_id, namespace, filters, discipline_module=''):
    """ load post processing regarding a namespace and a specific discipline inside this namespace

    :params: study_id, study to  load
    :type: integer
    :params: namespace, namespace key
    :type: str
    :params: filters, list of CHartFilter to use to filter post processings
    :filters: CHartFilter[]
    :params: discipline_module, specific object module to retrieve
    :type: str

    :return: tbd
    """
    # -- prepare execution
    study_manager.execution_engine.logger.info("\nSNAPSHOT BEFORE POSTPROC IN WEBAPI\n")
    snapshot = tracemalloc.take_snapshot()
    display_top(study_manager.execution_engine.logger, snapshot)
    study_manager = light_load_study_case(study_id)

    all_post_processing_data = []
    discipline_list = []
    post_processing_factory = PostProcessingFactory()
    try:
        discipline_list = study_manager.execution_engine.dm.get_disciplines_with_name(
            namespace)

        # Check if discipline of the node has to be filtered
        if not discipline_module == '':
            match_discipline = list(filter(
                lambda d: d.get_module() == discipline_module, discipline_list))

            if len(match_discipline) > 0:
                discipline_list = match_discipline
            else:
                discipline_list = []

        for discipline in discipline_list:
            post_processings = post_processing_factory.get_post_processing_by_discipline(
                discipline, filters)
            all_post_processing_data.extend(post_processings)

    except KeyError:
        pass
        # Discipline not found

    # Try fo find associated namespace object in namespace manager

    if discipline_module == PostProcessingFactory.NAMESPACED_POST_PROCESSING_NAME:
        post_processings = post_processing_factory.get_post_processing_by_namespace(
            study_manager.execution_engine, namespace, filters)

        all_post_processing_data.extend(post_processings)
    
    study_manager.execution_engine.logger.info("\nSNAPSHOT AFTER POSTPROC IN WEBAPI\n")
    snapshot = tracemalloc.take_snapshot()
    display_top(study_manager.execution_engine.logger, snapshot)
    
    return all_post_processing_data


def load_post_processing_graph_filters(study_id, discipline_key):
    """
        get post processing filters
        :params: study_id, study id
        :type: integer
        :params: discipline_key, key of the discipline to load
        :type: string
    """
    study_manager = light_load_study_case(study_id)

    if discipline_key in study_manager.execution_engine.dm.disciplines_dict:
        discipline = study_manager.execution_engine.dm.get_discipline(
            discipline_key)

        post_processing_factory = PostProcessingFactory()

        chart_filters = post_processing_factory.get_post_processing_filters_by_discipline(
            discipline)

        return chart_filters

    else:
        raise PostProcessingError(
            f'Discipline \'{discipline_key}\' does not exist in this study case.')


def reset_study_from_cache(study_id):
    """
        Reset study from cache
        :params: study_id, id of the study to load
        :type: integer
    """

    # Check if study is already in cache
    if study_case_cache.is_study_case_cached(study_id):
        # Remove outdated study from the cache
        study_case_cache.delete_study_case_from_cache(study_id)

        # Create the updated one
        study_manager = study_case_cache.get_study_case(study_id, False)

        return study_manager

