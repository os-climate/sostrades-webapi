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
tools methods to manage behaviour around StudyCase
"""

# pylint: disable=line-too-long

import traceback
import sys
from time import time
from sos_trades_core.tools.rw.load_dump_dm_data import DirectLoadDump
from sos_trades_api.models.database_models import StudyCase, \
    ReferenceStudy, StudyCaseExecutionLog, ReferenceStudyExecutionLog
from sos_trades_api.base_server import db
from sos_trades_api.tools.data_graph_validation.data_graph_validation import clean_obsolete_data_validation_entries
from sos_trades_api.controllers.sostrades_main.ontology_controller import generate_n2_matrix
from datetime import datetime, timezone
from sos_trades_core.execution_engine.sos_discipline import SoSDiscipline
from importlib import import_module
from eventlet import sleep



class StudyCaseError(Exception):
    """Base StudyCase Exception"""

    def __init__(self, msg=None):
        Exception.__init__(self, msg)

    def __str__(self):
        return self.__class__.__name__ + '(' + Exception.__str__(self) + ')'


class InvalidProcess(StudyCaseError):
    """Invalid process (Raise an error while trying to load it)"""


class InvalidStudy(StudyCaseError):
    """Invalid study"""


def study_need_to_be_updated(study_id, last_modification):
    """ Methods that check that the given study identifier last modification date is anterior
    to the database last modification date
    group identifier

    :params: study_id
    :type: int

    :params: last_modification
    :type: date

    :return: boolean (true is anterior)
    """
    from sos_trades_api.base_server import app

    with app.app_context():

        study_case = StudyCase.query.filter(
            StudyCase.id.like(study_id)).first()

        is_anterior = study_case.modification_date > last_modification
        app.logger.info(f'Check study identifier {study_id} database date/cached date ({study_case.modification_date}/{last_modification}) need to be updated {is_anterior}')

        if is_anterior:
            return True

    return False


def study_case_manager_loading(study_case_manager, no_data, read_only):
    """ Method that load data into a study case manager
        (usefull for threading study data loading)

    :params: study_case_manager, study case manager instance to load
    :type: StudyCaseManager

    :params: no_data, if treeview has to be loaded empty
    :type: boolean

    :params: read_only, if treeview has to be tagged read only
    :type: boolean


    """
    from sos_trades_api.base_server import app
    try:
        start_time = time()
        sleep()
        app.logger.info(
            f'Loading in background {study_case_manager.study.name}')
        study_case_manager.load_in_progress = True
        study_case_manager.loaded = False

        study_case_manager.load_data(display_treeview=False)
        load_data_time = time()

        study_case_manager.load_disciplines_data()
        load_discipline_data_time = time()

        study_case_manager.load_cache()
        load_cache_time = time()

        study_case_manager.execution_engine.dm.treeview = None

        study_case_manager.execution_engine.get_treeview(
            no_data, read_only)
        treeview_generation_time = time()

        study_case_manager.loaded = True
        study_case_manager.load_in_progress = False

        app.logger.info(
            f'End background loading {study_case_manager.study.name}, total time {treeview_generation_time - start_time} seconds')
        app.logger.info(f'Elapsed time synthesis:\n')
        app.logger.info(f'Data load {load_data_time - start_time} seconds\n')
        app.logger.info(f'Discipline data load {load_discipline_data_time - load_data_time} seconds\n')
        app.logger.info(f'Cache load {load_cache_time - load_discipline_data_time} seconds\n')
        app.logger.info(f'treeview gen. {treeview_generation_time - load_cache_time} seconds\n')

    except Exception as ex:
        study_case_manager.loaded = False
        study_case_manager.load_in_progress = False
        exc_type, exc_value, exc_traceback = sys.exc_info()
        study_case_manager.set_error(''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
        app.logger.exception(
            f'Error when loading in background {study_case_manager.study.name}')


def study_case_manager_update(study_case_manager, values, no_data, read_only, connectors=None):
    """ Method that inject data into a study case manager
        (usefull for threading study data loading)

    :params: study_case_manager, study case manager instance to load
    :type: StudyCaseManager

    :params: values, value to inject in study manager
    :type: dictionary

    :params: no_data, if treeview has to be loaded empty
    :type: boolean

    :params: read_only, if treeview has to be tagged read only
    :type: boolean

    :params: connectors, connectors to inject in study manager
    :type: dictionary
    """
    from sos_trades_api.base_server import app

    try:
        sleep()
        app.logger.info(
            f'Updating in background {study_case_manager.study.name}')

        study_case_manager.load_in_progress = True
        study_case_manager.loaded = False

        # Update parameter into dictionary
        study_case_manager.load_data(
            from_input_dict=values, display_treeview=False, from_connectors_dict=connectors)

        # Persist data using the current persistence strategy
        study_case_manager.dump_data(study_case_manager.dump_directory)
        study_case_manager.dump_disciplines_data(
            study_case_manager.dump_directory)
        study_case_manager.dump_cache(
            study_case_manager.dump_directory)

        # Get date
        modify_date = datetime.now().astimezone(timezone.utc).replace(tzinfo=None)

        # Update modification date on database
        with app.app_context():
            studycase = StudyCase.query.filter(
                StudyCase.id.like(study_case_manager.study.id)).first()
            studycase.modification_date = modify_date
            studycase.execution_status = ''

            db.session.add(studycase)
            db.session.commit()

        study_case_manager.execution_engine.dm.treeview = None

        study_case_manager.execution_engine.get_treeview(
            no_data, read_only)

        clean_obsolete_data_validation_entries(study_case_manager)

        study_case_manager.n2_diagram = {}
        study_case_manager.loaded = True
        study_case_manager.load_in_progress = False

        app.logger.info(
            f'End background updating {study_case_manager.study.name}')
    except Exception as ex:
        study_case_manager.loaded = False
        study_case_manager.load_in_progress = False
        exc_type, exc_value, exc_traceback = sys.exc_info()
        study_case_manager.set_error(''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
        app.logger.exception(
            f'Error when updating in background {study_case_manager.study.name}')


def study_case_manager_loading_from_reference(study_case_manager, no_data, read_only, reference_folder,
                                              reference_identifier):
    """ Method that initialize a study case manager instance with a reference
        (usefull for threading study data loading)

    :params: study_case_manager, study case manager instance to load
    :type: StudyCaseManager

    :params: no_data, if treeview has to be loaded empty
    :type: boolean

    :params: read_only, if treeview has to be tagged read only
    :type: boolean

    :params: reference_folder, folder that contains reference files
    :type: string

    :params: reference_identifier, reference identifier
    :type: string
    """
    try:
        sleep()
        from sos_trades_api.base_server import app
        app.logger.info(
            f'Loading reference in background {study_case_manager.study.name}')

        study_case_manager.load_in_progress = True
        study_case_manager.loaded = False

        # Reference are always persisted with a non crypted data, so in order to load them
        # we have to set the target study a non encrypted loader

        backup_rw_strategy = study_case_manager.rw_strategy
        study_case_manager.rw_strategy = DirectLoadDump()

        study_case_manager.load_data(reference_folder, display_treeview=False)
        study_case_manager.load_disciplines_data(reference_folder)
        study_case_manager.load_cache(reference_folder)

        # Restore original strategy for dumping
        study_case_manager.rw_strategy = backup_rw_strategy

        # Persist data using the current persistance strategy
        study_case_manager.dump_data(study_case_manager.dump_directory)
        study_case_manager.dump_disciplines_data(
            study_case_manager.dump_directory)
        study_case_manager.dump_cache(
            study_case_manager.dump_directory)

        study_case_manager.execution_engine.dm.treeview = None

        study_case_manager.execution_engine.get_treeview(
            no_data, read_only)

        study_case_manager.n2_diagram = {}
        study_case_manager.loaded = True
        study_case_manager.load_in_progress = False

        app.logger.info(
            f'End background reference loading {study_case_manager.study.name}')
    except Exception as ex:
        study_case_manager.loaded = False
        study_case_manager.load_in_progress = False
        exc_type, exc_value, exc_traceback = sys.exc_info()
        study_case_manager.set_error(''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)), True)
        app.logger.exception(
            f'Error when loading reference in background {study_case_manager.study.name}')


def study_case_manager_loading_from_usecase_data(study_case_manager, no_data, read_only, repository_name, process_name,
                                                 reference):
    """ Method that initialize a study case manager instance with a reference
        (usefull for threading study data loading)

    :params: study_case_manager, study case manager instance to load
    :type: StudyCaseManager

    :params: no_data, if treeview has to be loaded empty
    :type: boolean

    :params: read_only, if treeview has to be tagged read only
    :type: boolean

    :params: repository_name, name of the repository
    :type: string

    :params: process_name, name of the process
    :type: string

    :params: reference, name of the reference to load
    :type: string

    """
    try:
        sleep()
        from sos_trades_api.base_server import app
        app.logger.info(
            f'Loading usecase data in background {study_case_manager.study.name}')

        study_case_manager.load_in_progress = True
        study_case_manager.loaded = False

        imported_module = import_module(
            '.'.join([repository_name, process_name, reference]))
        imported_usecase = getattr(
            imported_module, 'Study')()

        imported_usecase.load_data()
        input_dict = imported_usecase.execution_engine.get_anonimated_data_dict()
        input_dict = {key: value[SoSDiscipline.VALUE]
                      for key, value in input_dict.items()}
        study_case_manager.load_data(from_input_dict=input_dict)

        # Persist data using the current persistance strategy
        study_case_manager.dump_data(study_case_manager.dump_directory)
        study_case_manager.dump_disciplines_data(
            study_case_manager.dump_directory)
        study_case_manager.dump_cache(
            study_case_manager.dump_directory)

        study_case_manager.execution_engine.dm.treeview = None

        study_case_manager.execution_engine.get_treeview(
            no_data, read_only)

        study_case_manager.n2_diagram = {}
        study_case_manager.loaded = True
        study_case_manager.load_in_progress = False

        app.logger.info(
            f'End of loading usecase data in background {study_case_manager.study.name}')
    except Exception as ex:
        study_case_manager.loaded = False
        study_case_manager.load_in_progress = False
        exc_type, exc_value, exc_traceback = sys.exc_info()
        study_case_manager.set_error(''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)), True)
        app.logger.exception(
            f'Error when loading usecase data in background {study_case_manager.study.name}')


def study_case_manager_loading_from_study(study_case_manager, no_data, read_only, source_study):
    """ Method that initialize a study case manager instance with a reference
        (usefull for threading study data loading)

    :params: study_case_manager, study case manager instance to load
    :type: StudyCaseManager

     :params: no_data, if treeview has to be loaded empty
    :type: boolean

    :params: read_only, if treeview has to be tagged read only
    :type: boolean

    :params: source_study, source study to load
    :type: string
    """
    try:
        sleep()
        from sos_trades_api.base_server import app
        app.logger.info(
            f'Loading from study in background {study_case_manager.study.name}')

        study_case_manager.load_in_progress = True
        study_case_manager.loaded = False

        # To initiliaze the target study with the source study we use the
        # read/write strategy of the source study
        backup_rw_strategy = study_case_manager.rw_strategy

        study_case_manager.rw_strategy = source_study.rw_strategy
        study_case_manager.load_data(
            source_study.dump_directory, display_treeview=False)
        study_case_manager.load_disciplines_data(source_study.dump_directory)
        study_case_manager.load_cache(source_study.dump_directory)

        # Restore original strategy for dumping
        study_case_manager.rw_strategy = backup_rw_strategy

        # Persist data using the current persistance strategy
        study_case_manager.dump_data(study_case_manager.dump_directory)
        study_case_manager.dump_disciplines_data(
            study_case_manager.dump_directory)
        study_case_manager.dump_cache(study_case_manager.dump_directory)

        study_case_manager.execution_engine.dm.treeview = None

        study_case_manager.execution_engine.get_treeview(
            no_data, read_only)

        study_case_manager.n2_diagram = {}
        study_case_manager.loaded = True
        study_case_manager.load_in_progress = False

        app.logger.info(
            f'End of loading from study in background {study_case_manager.study.name}')
    except Exception as ex:

        study_case_manager.loaded = False
        study_case_manager.load_in_progress = False
        exc_type, exc_value, exc_traceback = sys.exc_info()
        study_case_manager.set_error(''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)), True)
        app.logger.exception(
            f'Error when loading from study in background {study_case_manager.study.name}')


