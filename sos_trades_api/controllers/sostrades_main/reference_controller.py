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
from sos_trades_api.base_server import db
from sos_trades_api.models.database_models import ReferenceStudy
from sos_trades_api.tools.kubernetes.kubernetes_service import kubernetes_service_generate
from sos_trades_api.tools.reference_management.reference_generation_subprocess import ReferenceGenerationSubprocess
from sos_trades_api.config import Config


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

        return gen_ref_status.id


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
        Get a reference execution status from path
    """
    ref = ReferenceStudy.query \
        .filter(ReferenceStudy.reference_path == reference_path).first()

    if ref is not None:
        return ref.execution_status
    else:
        return ReferenceStudy.UNKNOWN
