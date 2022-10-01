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
Reference Functions
"""
from tempfile import gettempdir
import io
from sos_trades_api.server.base_server import db

from sos_trades_api.tools.right_management.functional.process_access_right import ProcessAccess

from sos_trades_api.models.database_models import ReferenceStudy, ReferenceStudyExecutionLog
from sos_trades_api.models.study_case_dto import StudyCaseDto
from sos_trades_api.controllers.sostrades_data.ontology_controller import load_processes_metadata, load_repositories_metadata
from sos_trades_api.tools.kubernetes.kubernetes_service import kubernetes_eeb_service_pods_status, kubernetes_service_generate
from sos_trades_api.config import Config
from sos_trades_api.tools.reference_management.reference_generation_subprocess import ReferenceGenerationSubprocess


def generate_reference(repository_name, process_name, usecase_name, user_id):
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
    is_generating = check_reference_is_regenerating(
        reference_path=reference_path)
    if is_generating is True:
        # Already running -> return the id
        generation_running = ReferenceStudy.query\
            .filter(ReferenceStudy.reference_path == reference_path,
                    ReferenceStudy.execution_status.in_([
                        ReferenceStudy.RUNNING,
                        ReferenceStudy.PENDING])).first()
        return generation_running.id
    else:
        gen_ref_status = ReferenceStudy.query \
            .filter(ReferenceStudy.reference_path == reference_path).first()
        gen_ref_status.execution_status = gen_ref_status.PENDING
        gen_ref_status.user_id = user_id

        db.session.add(gen_ref_status)
        db.session.commit()
        try:
            if Config().execution_strategy == Config.CONFIG_EXECUTION_STRATEGY_K8S:
                # Launch pod whom generate the ref
                pod_name = kubernetes_service_generate(
                    reference_path, gen_ref_status.id, user_id)
                # Update db by adding the pod whom generate the ref
                gen_ref_status.kubernete_pod_name = pod_name
                db.session.add(gen_ref_status)
                db.session.commit()
            else:
                subprocess_generation = ReferenceGenerationSubprocess(
                    gen_ref_status.id)
                subprocess_generation.run()
        except Exception as ex:
            ReferenceStudy.query.filter(ReferenceStudy.id == gen_ref_status.id).update(
                {
                    'execution_status': ReferenceStudy.FAILED,
                    'generation_logs': ex,
                    'creation_date': None,
                }
            )
            db.session.commit()
            raise ex

        return gen_ref_status.id


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
        for ref in process_references:

            new_usecase = StudyCaseDto()
            new_usecase.name = ref.name
            new_usecase.process = authorized_process.process_id
            new_usecase.repository = authorized_process.repository_id
            new_usecase.description = 'Reference'
            new_usecase.creation_date = ref.creation_date
            new_usecase.study_type = ref.reference_type
            new_usecase.group_id = None
            new_usecase.group_name = 'All groups'

            # Apply ontology on the usecase
            new_usecase.apply_ontology(process_metadata, repository_metadata)

            # Check if generation is running
            is_running = check_reference_is_regenerating(ref.reference_path)
            if is_running:
                new_usecase.is_reference_running = is_running
                new_usecase.regeneration_id = ref.id
            # Get generation status
            gen_status = get_reference_execution_status_by_name(ref.reference_path)
            new_usecase.regeneration_status = gen_status
            if new_usecase.creation_date is not None:
                if gen_status == ReferenceStudy.UNKNOWN:
                    new_usecase.regeneration_status = ReferenceStudy.FINISHED
            result.append(new_usecase)

    if len(result) > 0:
        result = sorted(
            result, key=lambda res: res.process_display_name.lower())
    return result


def get_reference_generation_status(ref_gen_id):
    '''
        Get the status of a generation, looked by id
        Also check if the generation is running in the container
        or if an error happened
        :params: ref_gen_id
        :type: Int
        :return: Dictionnary containing ref gen id, status of the generation, logs associated to the generation
        :type: Dict
    '''
    # Retrieve ongoing generation from db
    ref_generation = ReferenceStudy.query.filter(
        ReferenceStudy.id == ref_gen_id).first()
    if ref_generation is not None:
        result = ref_generation
        # Get pod status
        if Config().execution_strategy == Config.CONFIG_EXECUTION_STRATEGY_K8S:
            pod_status = kubernetes_eeb_service_pods_status(
                ref_generation.kubernete_pod_name).get(ref_generation.kubernete_pod_name)
        else:
            pod_status = 'Running'
        if (ref_generation.execution_status == ReferenceStudy.RUNNING or
                ref_generation.execution_status == ReferenceStudy.PENDING)\
                and pod_status not in ['Running', 'Pending']:
            # Generation running and pod not running -> ERROR
            error_msg = 'Regeneration status not coherent.'
            # Update generation in db to FAILED
            ReferenceStudy.query.filter(ReferenceStudy.id == ref_gen_id)\
                .update({'execution_status': ReferenceStudy.FAILED,
                         'generation_logs': error_msg})
            db.session.commit()
            result.execution_status = ReferenceStudy.FAILED
            result.generation_logs = error_msg
    else:
        result = ReferenceStudy()
        result.id = ref_gen_id
        result.execution_status = ReferenceStudy.UNKNOWN
        result.generation_logs = 'Error cannot retrieve reference generation from database'
    return result


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
        result = ref_generation
    else:
        result = ReferenceStudy()
        result.id = None
        result.execution_status = ReferenceStudy.UNKNOWN
        result.generation_logs = 'Error cannot retrieve reference generation from database'
    return result


def get_references_generation_status(references_list):
    refs_status = []
    for ref in references_list:
        ref_status = get_reference_generation_status_by_name(
            ref['repository'], ref['process'], ref['name'])
        refs_status.append(ref_status)
    return refs_status


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


def check_reference_is_regenerating(reference_path):
    '''
        Check if a reference is in RUNNING phase in the db
        :params: reference_path name of the reference we are looking for
        :type: String
        :return: True if generating, false otherwise
        :type: Boolean
    '''
    # Retrieve ongoing generation from db
    ref_is_running = False
    generation_is_running = ReferenceStudy.query\
        .filter(ReferenceStudy.reference_path == reference_path).first()

    if generation_is_running:
        if generation_is_running.execution_status == ReferenceStudy.PENDING \
                or generation_is_running.execution_status == ReferenceStudy.RUNNING:
            ref_is_running = True

    return ref_is_running


def get_reference_execution_status_by_name(reference_path):
    """
    Get the status of a reference
    :param: reference_path, path of the reference to get
    :type: string
    """
    ref = ReferenceStudy.query \
        .filter(ReferenceStudy.reference_path == reference_path).first()

    if ref is not None:
        return ref.execution_status
    else:
        return ReferenceStudy.UNKNOWN