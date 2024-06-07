'''
Copyright 2022 Airbus SAS
Modifications on 2023/11/22-2024/04/11 Copyright 2023 Capgemini
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
Reference Functions
"""
import io
import os
import signal
from tempfile import gettempdir
from typing import Optional

from sos_trades_api.config import Config
from sos_trades_api.controllers.sostrades_data.ontology_controller import (
    load_processes_metadata,
    load_repositories_metadata,
)
from sos_trades_api.models.database_models import (
    PodAllocation,
    ReferenceStudy,
    ReferenceStudyExecutionLog,
)
from sos_trades_api.models.study_case_dto import StudyCaseDto
from sos_trades_api.server.base_server import app, db
from sos_trades_api.tools.allocation_management.allocation_management import (
    create_and_load_allocation,
    delete_pod_allocation,
    get_allocation_status,
)
from sos_trades_api.tools.reference_management.reference_generation_subprocess import (
    ReferenceGenerationSubprocess,
)
from sos_trades_api.tools.right_management.functional.process_access_right import (
    ProcessAccess,
)


def generate_reference(repository_name:str, process_name:str, usecase_name:str, user_id:int):
    '''
        Generate a reference
        :params: repository_name
        :type: String
        :params: process_name
        :type: String
        :params: usecase_name
        :type: String
        :params: user_id
        :type: Int
        :return: gen_ref_status.id, id of the generation just launched
        :type: Int
    '''
    # Build full name
    reference_path = '.'.join([repository_name, process_name, usecase_name])

    # Check if already runing
    # Already running -> return the id
    generation_running = ReferenceStudy.query\
        .filter(ReferenceStudy.reference_path == reference_path,
                ReferenceStudy.execution_status.in_([
                    ReferenceStudy.RUNNING,
                    ReferenceStudy.PENDING])).first()
    if generation_running is not None:
        return generation_running.id
    else:
        gen_ref_status = ReferenceStudy.query \
            .filter(ReferenceStudy.reference_path == reference_path).first()
        gen_ref_status.execution_status = gen_ref_status.PENDING
        gen_ref_status.user_id = user_id

        db.session.add(gen_ref_status)
        db.session.commit()

        #create pod allocation, launch pod in case of kubernetes strategy
        new_pod_allocation = create_and_load_allocation(gen_ref_status.id, 
                                                        PodAllocation.TYPE_REFERENCE, 
                                                        gen_ref_status.generation_pod_flavor)
        try:
            # if execution is not kubernetes, lunch generation in subprocess
            if Config().execution_strategy != Config.CONFIG_EXECUTION_STRATEGY_K8S:
                subprocess_generation = ReferenceGenerationSubprocess(
                    gen_ref_status.id)
                subprocess_id = subprocess_generation.run()
                ReferenceStudy.query.filter(ReferenceStudy.id == gen_ref_status.id).update(
                {
                    'execution_thread_id': subprocess_id
                }
                )
                db.session.commit()

        except Exception as ex:
            ReferenceStudy.query.filter(ReferenceStudy.id == gen_ref_status.id).update(
                {
                    'execution_status': ReferenceStudy.FAILED,
                    'generation_logs': str(ex),
                    'creation_date': None,
                }
            )
            db.session.commit()
            raise ex

        return gen_ref_status.id

def update_reference_flavor(ref_gen_id, selected_flavor:str)->bool:
    '''
        save the new selected flavor in database
        :params ref_gen_id:  id of the reference to update
        :type ref_gen_id: Int
        :params selected_flavor: selected flavor name
        :type selected_flavor: string
        :return: reference is updated
        :type: boolean
    '''
    # Retrieve ongoing generation from db
    updated = False
    ref_generation = ReferenceStudy.query.filter(
        ReferenceStudy.id == ref_gen_id).first()
    if ref_generation is not None:
       ref_generation.generation_pod_flavor = selected_flavor
       db.session.add(ref_generation)
       db.session.commit()
       updated = True
    return updated

def get_reference_flavor(ref_gen_id)->str:
    '''
        get the reference flavor in database
        :params ref_gen_id:  id of the reference to get
        :type ref_gen_id: Int
        :return: reference pod size
        :type: string
    '''
    # Retrieve ongoing generation from db
    flavor = ""
    ref_generation = ReferenceStudy.query.filter(
        ReferenceStudy.id == ref_gen_id).first()
    if ref_generation is not None:
       flavor = ref_generation.generation_pod_flavor

    return flavor

def get_all_references(user_id, logger):
    '''
        Get all references present on the disk
        :params: user_id
        :type: Int
        :params: logger
        :type: ?
        :return: result, List containing all the references found
        :type: List[StudyCaseDto]
    '''
    all_references_proc_ref_tuple_list = []

    all_references = ReferenceStudy.query.all()
    process_access = ProcessAccess(user_id)
    authorized_process_list = process_access.get_authorized_process()

    # Apply Ontology
    processes_metadata = []
    repositories_metadata = []
    for authorized_process in authorized_process_list:
        process_key = f'{authorized_process.repository_id}.{authorized_process.process_id}'
        if process_key not in processes_metadata:
            processes_metadata.append(process_key)

        repository_key = authorized_process.repository_id
        if repository_key not in repositories_metadata:
            repositories_metadata.append(repository_key)

    process_metadata = load_processes_metadata(processes_metadata)
    repository_metadata = load_repositories_metadata(repositories_metadata)

    for authorized_process in authorized_process_list:
        # Retrieve references for process
        process_references = list(filter(lambda ref_process: ref_process.process_id == authorized_process.id
                            and (authorized_process.is_manager or authorized_process.is_contributor), all_references))
        for proc_ref in process_references:

            new_usecase = StudyCaseDto()
            new_usecase.name = proc_ref.name
            new_usecase.process = authorized_process.process_id
            new_usecase.process_display_name = authorized_process.process_id
            new_usecase.repository = authorized_process.repository_id
            new_usecase.repository_display_name = authorized_process.repository_id
            new_usecase.regeneration_id = proc_ref.id
            new_usecase.description = 'Reference'
            new_usecase.creation_date = proc_ref.creation_date
            new_usecase.study_type = proc_ref.reference_type
            new_usecase.group_id = None
            new_usecase.group_name = 'All groups'
            new_usecase.generation_pod_flavor = proc_ref.generation_pod_flavor

            # Apply ontology on the usecase
            new_usecase.apply_ontology(process_metadata, repository_metadata)

            all_references_proc_ref_tuple_list.append([proc_ref, new_usecase])

    # Get a list of all proc refs
    all_procs_refs = [elem[0] for elem in all_references_proc_ref_tuple_list]

    # Get status as a list
    all_procs_refs_execution_status_dict = get_generation_status_list(all_procs_refs)
    for proc_ref, new_usecase in all_references_proc_ref_tuple_list: 
        proc_ref = all_procs_refs_execution_status_dict[proc_ref.id]
        new_usecase.is_reference_running = check_reference_is_regenerating(proc_ref)
        # Check if generation is running
        new_usecase.regeneration_id = proc_ref.id
        new_usecase.regeneration_status = proc_ref.execution_status
        new_usecase.error = proc_ref.generation_logs

    result = [elem[1] for elem in all_references_proc_ref_tuple_list]

    if len(result) > 0:
        result = sorted(
            result, key=lambda res: res.process_display_name.lower())
    return result

def get_generation_status_list(reference_list: list[ReferenceStudy]) -> dict[int, ReferenceStudy]:
    '''
    Update pod allocation from ReferenceStudy list and commit to database
    '''
    result_dict = {}
    reference_ids_list = [reference.id for reference in reference_list]
    pod_allocations_dict = get_reference_allocation_and_status_list(reference_ids_list)

    for reference in reference_list:
        result_dict[reference.id] = reference
        pod_allocation = pod_allocations_dict[reference.id]

        if pod_allocation is not None:
            get_reference_status_from_allocation(reference, pod_allocation)
            result_dict[reference.id] = reference
            
            db.session.add(pod_allocation)
            db.session.commit()
        
    return result_dict

def stop_generation(reference_id):
    '''
    stop the generation of the reference, kill the pod in case of kubernetes execution
    '''
    reference = ReferenceStudy.query.filter(ReferenceStudy.id.like(reference_id)).first()

    if reference is not None:
        try:  
            is_kubernetes_execution = Config().execution_strategy == Config.CONFIG_EXECUTION_STRATEGY_K8S
            pod_allocation = get_reference_allocation_and_status(reference_id)
            app.logger.info("Retrieved status of pod of kubernetes from stop_generation()")

            # try delete pod associated
            if pod_allocation is not None:
                delete_pod_allocation(pod_allocation, is_kubernetes_execution and pod_allocation.pod_status != PodAllocation.NOT_STARTED)
            
            if not is_kubernetes_execution and reference.execution_thread_id is not None and reference.execution_thread_id > 0:
                try:
                    os.kill(reference.execution_thread_id,signal.SIGTERM)
                except Exception as ex:
                    app.logger.exception(
                            f'This error occurs when trying to kill process {reference.execution_thread_id}')

            # Update execution
            reference = ReferenceStudy.query.filter(ReferenceStudy.id.like(reference_id)).first()
            reference.execution_status = ReferenceStudy.STOPPED
            db.session.add(reference)
            db.session.commit()

        except Exception as error:

            # Update execution before submitted process
            reference_study = ReferenceStudy.query.filter(ReferenceStudy.id == reference_id).first()
            reference_study.generation_logs = error
            reference.execution_status = ReferenceStudy.STOPPED
            db.session.add(reference_study)
            db.session.commit()

            raise error


def get_generation_status(reference: ReferenceStudy):
    '''
    Get reference status from pod allocation
    '''
    result = reference

    # Get pod allocation
    pod_allocation = get_reference_allocation_and_status(reference.id)
    if pod_allocation is not None:
        get_reference_status_from_allocation(result, pod_allocation)
        
        db.session.add(pod_allocation)
        db.session.commit()
        
    return result

def get_reference_status_from_allocation(reference, pod_allocation):
    error_msg = ''
    pod_status = ''
    if Config().execution_strategy == Config.CONFIG_EXECUTION_STRATEGY_K8S:
        pod_status = f' - pod status:{pod_allocation.pod_status}'
    # if the execution is at running (meaning it has already started) but the pod is not running anymore
    # it means it has failed : save failed status and save error msg
    if (reference.execution_status == ReferenceStudy.RUNNING \
            and not (pod_allocation.pod_status == PodAllocation.RUNNING or pod_allocation.pod_status == PodAllocation.COMPLETED)) or \
            (pod_allocation.pod_status == PodAllocation.IN_ERROR or pod_allocation.pod_status == PodAllocation.OOMKILLED):
        # Generation running and pod not running -> ERROR
        error_msg = ' - Regeneration status not coherent.'
        if pod_allocation.message is not None and pod_allocation.message != '':
            if pod_allocation.pod_status == PodAllocation.OOMKILLED:
                error_msg = ' - pod error message: The pod had not enough resources, you may need to choose a bigger pod size for this reference'
            else:
                error_msg = f' - pod error message: {pod_allocation.message}'
    
        # Update generation in db to FAILED
        ReferenceStudy.query.filter(ReferenceStudy.id == reference.id)\
            .update({'execution_status': ReferenceStudy.POD_ERROR,
                    'generation_logs': pod_status + error_msg})
        
        reference.execution_status = ReferenceStudy.POD_ERROR
        reference.generation_logs = pod_status + error_msg
    # if pod is pending, execution too
    elif pod_allocation.pod_status == PodAllocation.PENDING:
        reference.execution_status = ReferenceStudy.PENDING
        reference.generation_logs = '- Pod is loading'


def get_reference_generation_status_by_id(ref_gen_id):
    '''
        Get the status of a generation, looked by id
        Also check if the generation is running in the container
        or if an error happened
        :params: ref_gen_id
        :type: Int
        :return: reference Study with updated status
        :type: ReferenceStudy
    '''
    # Retrieve ongoing generation from db
    ref_generation = ReferenceStudy.query.filter(
        ReferenceStudy.id == ref_gen_id).first()
    if ref_generation is not None:
       ref_generation = get_generation_status(ref_generation)
    return ref_generation


def get_logs(reference_path=None):
    """
    Get logs from a reference
    """
    logs = []

    if reference_path is not None:
        ref_generation = ReferenceStudy.query.filter(
            ReferenceStudy.reference_path == reference_path).first()
        if ref_generation is not None:
            # Retrieve logs from ref generation and add it to the sc log
            logs = ReferenceStudyExecutionLog.query.filter(
                ReferenceStudyExecutionLog.reference_id == ref_generation.id).\
                order_by(ReferenceStudyExecutionLog.id.asc()).all()
    if logs:
        tmp_folder = gettempdir()
        file_name = f'{tmp_folder}/{reference_path}_log'
        with io.open(file_name, "w", encoding="utf-8") as f:
            for log in logs:
                f.write(f'{log.created}\t{log.name}\t{log.log_level_name}\t{log.message}\t{log.exception}\n')
        return file_name


def check_reference_is_regenerating(reference: ReferenceStudy):
    '''
        Check if a reference is in RUNNING phase in the db
        :params: reference_path name of the reference we are looking for
        :type: String
        :return: True if generating, false otherwise
        :type: Boolean
    '''
    # Retrieve ongoing generation from db
    ref_is_running = False
    
    if reference.execution_status == ReferenceStudy.PENDING \
                or reference.execution_status == ReferenceStudy.RUNNING:
            ref_is_running = True

    return ref_is_running


def get_reference_allocation_and_status(reference_id)-> PodAllocation:
    """
    get allocation and check allocation pod status
    """
    pod_allocations = PodAllocation.query.filter(PodAllocation.identifier == reference_id).filter(
                                                        PodAllocation.pod_type == PodAllocation.TYPE_REFERENCE
                                                        ).order_by(PodAllocation.creation_date.asc()).all()
    reference_allocation = None
    if len(pod_allocations) > 0:
        reference_allocation = pod_allocations[-1]
        reference_allocation.pod_status, reference_allocation.message = get_allocation_status(reference_allocation)
        if len(pod_allocations) > 1:
            app.logger.warning(f"We have {len(pod_allocations)} pod allocations for the same reference (id {reference_id}) but only one will be updated, is this normal ?")
        
    return reference_allocation


def get_reference_allocation_and_status_list(reference_ids:list[int])-> dict[int: Optional[PodAllocation]]:
    """
    Get allocation and check allocation pod status for a list of reference IDs
    """
    reference_allocations = {}
    
    # Fetch pod allocations for all reference IDs in a single query
    pod_allocations = PodAllocation.query.filter(
        PodAllocation.identifier.in_(reference_ids),
        PodAllocation.pod_type == PodAllocation.TYPE_REFERENCE
    ).all()
    
    # Group pod allocations by reference ID
    allocations_by_reference = {}
    for allocation in pod_allocations:
        allocations_by_reference.setdefault(allocation.identifier, []).append(allocation)
    
    # Find the most recent allocation for each reference ID
    for reference_id in reference_ids:
        allocations = allocations_by_reference.get(reference_id, [])
        if len(allocations) == 0:
            reference_allocations[reference_id] = None
        else:
            most_recent_allocation = max(allocations, key=lambda x: x.creation_date)
            reference_allocations[reference_id] = most_recent_allocation
            
            if len(allocations) > 1:
                app.logger.warning(f"We have {len(allocations)} pod allocations for the same reference (id {reference_id}) but only one will be updated, is this normal ?")
        
    return reference_allocations

