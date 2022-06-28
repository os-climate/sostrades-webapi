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
import traceback
from sos_trades_api.models.database_models import ReferenceStudy, User, Process
from sos_trades_api.tools.right_management.functional.process_access_right import ProcessAccess
from sos_trades_api.controllers.sostrades_main.ontology_controller import load_processes_metadata, \
    load_repositories_metadata, load_ontology_processes
from sos_trades_api.models.study_case_dto import StudyCaseDto
from sos_trades_api.models.loaded_process import LoadedProcess
from typing import List


class ProcessError(Exception):
    """Base Process Exception"""

    def __init__(self, msg=None):

        message = None
        if msg is not None:
            if isinstance(msg, Exception):
                message = f'the following exception occurs {msg}.\n{traceback.format_exc()}'
            else:
                message = msg

        Exception.__init__(self, message)

    def __str__(self):
        return self.__class__.__name__ + '(' + Exception.__str__(self) + ')'


def api_get_processes_for_user(user: User) -> List[LoadedProcess]:
    """
    Ask execution engine to retrieve all available processes for the current user

    :param user: user for which process has to be filtered
    """

    process_access = ProcessAccess(user_id=user.id)
    authorized_process_list = process_access.get_authorized_process()

    apply_ontology_to_loaded_process(authorized_process_list)

    # Adding reference list
    all_references = ReferenceStudy.query.filter(ReferenceStudy.execution_status == ReferenceStudy.FINISHED).all()

    for authorized_process in authorized_process_list:
        process_references = list(
            filter(lambda ref_process: ref_process.process_id == authorized_process.id, all_references))
        process_ref_list = []
        for ref in process_references:
            new_ref = StudyCaseDto()
            new_ref.name = ref.reference_path.split(".")[-1]
            new_ref.process_display_name = authorized_process.process_name
            new_ref.repository_display_name = authorized_process.repository_name
            new_ref.process = authorized_process.process_id
            new_ref.repository = authorized_process.repository_id
            new_ref.creation_date = ref.creation_date
            new_ref.group_id = None
            new_ref.group_name = 'All groups'

            if ref.reference_type == ReferenceStudy.TYPE_REFERENCE:
                new_ref.description = 'Reference study'
                new_ref.study_type = 'Reference'
            else:
                new_ref.description = 'Usecase data'
                new_ref.study_type = 'UsecaseData'
            process_ref_list.append(new_ref)

        if len(process_ref_list) > 0:
            authorized_process.reference_list = process_ref_list

    # Sort by process display name
    if len(authorized_process_list) > 0:
        authorized_process_list = sorted(
            authorized_process_list, key=lambda res: res.process_name.lower())
    return authorized_process_list


def api_get_processes_for_dashboard() -> List[LoadedProcess]:
    """
    Retrieve all database processes

    """
    all_processes = Process.query.all()

    results = []

    for process in all_processes:
        new_loaded_process = LoadedProcess(process.id, process.name, process.process_path)
        new_loaded_process.is_manager = True
        results.append(new_loaded_process)

    apply_ontology_to_loaded_process(results)

    return results


def apply_ontology_to_loaded_process(loaded_processes: List[LoadedProcess]) -> List[LoadedProcess]:
    """
    Apply ontology to each loaded process elements
    :param loaded_processes: process on which ontology has to be applied
    """

    # Retrieve full processes ontology
    processes = load_ontology_processes()

    for authorized_process in loaded_processes:
        authorized_process.apply_ontology(processes)

    print(processes)