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
from tempfile import gettempdir
import io
import os
import signal
from sos_trades_api.tools.allocation_management.allocation_management import create_and_load_allocation, get_allocation_status, delete_pod_allocation
from sos_trades_api.server.base_server import db, app

from sos_trades_api.tools.right_management.functional.process_access_right import ProcessAccess

from sos_trades_api.models.database_models import PodAllocation, ReferenceStudy, ReferenceStudyExecutionLog
from sos_trades_api.models.study_case_dto import StudyCaseDto
from sos_trades_api.controllers.sostrades_data.ontology_controller import load_processes_metadata, load_repositories_metadata
from sos_trades_api.config import Config
from sos_trades_api.tools.reference_management.reference_generation_subprocess import ReferenceGenerationSubprocess


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
    result = []

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

            # Check if generation is running
            proc_ref = get_generation_status(proc_ref)
            new_usecase.is_reference_running = check_reference_is_regenerating(proc_ref)
            new_usecase.regeneration_id = proc_ref.id
            new_usecase.regeneration_status = proc_ref.execution_status
            new_usecase.error = proc_ref.generation_logs
            result.append(new_usecase)

    if len(result) > 0:
        result = sorted(
            result, key=lambda res: res.process_display_name.lower())
    return result

def stop_generation(reference_id):
    '''
    stop the generation of the reference, kill the pod in case of kubernetes execution
    '''
    reference = ReferenceStudy.query.filter(ReferenceStudy.id.like(reference_id)).first()

    if reference is not None:
        try:  
            is_kubernetes_execution = Config().execution_strategy == Config.CONFIG_EXECUTION_STRATEGY_K8S
            pod_allocation = get_reference_allocation_and_status(reference_id)
            # try delete pod associated
            if pod_allocation is not None:
                delete_pod_allocation(pod_allocation, is_kubernetes_execution)
            
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
            ReferenceStudy.query.filter(ReferenceStudy.id.like(reference_id)).update({
                'generation_logs':str(error)
            })
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
        error_msg = ''
        pod_status = ''
        if Config().execution_strategy == Config.CONFIG_EXECUTION_STRATEGY_K8S:
            pod_status = f' - pod status:{pod_allocation.pod_status}'
        # if the execution is at running (meaning it has already started) but the pod is not running anymore
        # it means it has failed : save failed status and save error msg
        if (reference.execution_status == ReferenceStudy.RUNNING \
                and not (pod_allocation.pod_status == PodAllocation.RUNNING or pod_allocation.pod_status == PodAllocation.COMPLETED)):
            # Generation running and pod not running -> ERROR
            error_msg = ' - Regeneration status not coherent.'
            if pod_allocation.message is not None and pod_allocation.message != '':
                error_msg = f' - pod error message:{pod_allocation.message}'
            # Update generation in db to FAILED
            ReferenceStudy.query.filter(ReferenceStudy.id == reference.id)\
                .update({'execution_status': ReferenceStudy.POD_ERROR,
                        'generation_logs': pod_status + error_msg})
            
            result.execution_status = ReferenceStudy.POD_ERROR
            result.generation_logs = pod_status + error_msg
        # if pod is pending, execution too
        elif pod_allocation.pod_status == PodAllocation.PENDING:
            result.execution_status = ReferenceStudy.PENDING
            result.generation_logs = '- Pod is loading'
        
        db.session.add(pod_allocation)
        db.session.commit()
        
    return result


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


def get_reference_generation_status_by_name(repository_name, process_name, usecase_name):
    '''
        Get the status of a generation, looked by name
        :params: repository_name
        :type: String
        :params: process_name
        :type: String
        :params: usecase_name
        :type: String
        :return: Dictionnary containing ref gen id, status of the generation, logs associated to the generation
        :type: Dict
    '''
    ref_name = f'{repository_name}.{process_name}.{usecase_name}'
    # Retrieve ongoing generation from db
    ref_generation = ReferenceStudy.query.filter(
        ReferenceStudy.reference_path == ref_name).first()

    if ref_generation is not None:
        result = get_generation_status(ref_generation)
    else:
        result = ReferenceStudy()
        result.id = None
        result.execution_status = ReferenceStudy.UNKNOWN
        result.generation_logs = 'Error cannot retrieve reference generation from database'
    return result


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
    pod_allocation = PodAllocation.query.filter(PodAllocation.identifier == reference_id).filter(
                                                PodAllocation.pod_type == PodAllocation.TYPE_REFERENCE
                                                ).order_by(PodAllocation.creation_date.asc()).last()
    if pod_allocation is not None:
        pod_allocation.pod_status, pod_allocation.message = get_allocation_status(pod_allocation)
        
    return pod_allocation

def get_reference_execution_status_by_name(reference_path):
    """
    Get the status of a reference
    :param: reference_path, path of the reference to get
    :type: string
    """
    ref = ReferenceStudy.query \
        .filter(ReferenceStudy.reference_path == reference_path).first()
    if ref is not None:
        reference_status = ref.execution_status
        # get allocation
        pod_allocation = get_reference_allocation_and_status(ref.id)
        if pod_allocation is not None:
            # Reference status is running, pod has been killed
            if (pod_allocation.pod_status != PodAllocation.RUNNING and reference_status == ReferenceStudy.RUNNING):
                reference_status = ReferenceStudy.FAILED
        return reference_status
    else:
        return ReferenceStudy.UNKNOWN