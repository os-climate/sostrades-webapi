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
Reference management
"""
from sos_trades_api.base_server import db
from sos_trades_api.config import Config
from importlib import import_module
from os.path import isdir, join, dirname
from os import listdir, stat
from datetime import datetime, timezone
from sos_trades_api.models.database_models import Process, ReferenceStudy


def update_database_with_references(logger=None):
    """ Method that retrieve all available references and inject them into database
        If a reference already exist in database it will be enabled or disabled regarding
        is the reference is found into the source code

        The methods check for processes using:
        - The PYTHONPATH environment variable
        - A list set in flask server configuration ('SOS_TRADES_PROCESS_REPOSITORY' key)

        :params: logger, logging message
        :type: Logger
    """
    # Retrieve reference base path
    reference_basepath = Config().reference_root_dir

    # Retrieve all references from database
    all_database_references = ReferenceStudy.query.all()

    # Disabled all existing references
    for reference in all_database_references:
        reference.disabled = True
        db.session.add(reference)
    logger.info(f'{len(all_database_references)} existing references disabled found')

    # Retrieve all existing process from database
    all_database_processes = Process.query.all()

    new_references_count = 0
    enabled_references_count = 0

    # Looping through processes to check reference(s) per process
    for process in all_database_processes:
        # Retrieve process module
        imported_module = import_module('.'.join([process.process_path, process.name]))
        if imported_module.__file__ is not None:
            process_directory = dirname(imported_module.__file__)
            # Loop through activated usecases in folder
            for usecase_py in listdir(process_directory):
                if usecase_py.startswith('usecase'):
                    usecase = usecase_py.replace('.py', '')
                    # Check if imported_usecase is already generated
                    if isdir(join(reference_basepath, process.process_path, process.name, usecase)):
                        dm_pkl_exists = True
                    else:
                        dm_pkl_exists = False

                    is_uc_data = is_usecase_data(process, usecase, logger)
                    if is_uc_data is not None:
                        if is_usecase_data(process, usecase, logger):
                            ref_type = ReferenceStudy.TYPE_USECASE_DATA
                        else:
                            ref_type = ReferenceStudy.TYPE_REFERENCE
                        # Save reference in database
                        enabled_ref, new_ref = save_reference_in_database(process, usecase, all_database_references,
                                                                          reference_basepath, ref_type, dm_pkl_exists,
                                                                          logger)
                        enabled_references_count += enabled_ref
                        new_references_count += new_ref

    logger.info(f'{new_references_count} new reference(s) found')
    logger.info(f'{enabled_references_count} enabled reference(s)')

    disabled_references = ReferenceStudy.query.filter(ReferenceStudy.disabled == True).all()

    if len(disabled_references) > 0:
        logger.info(f'{len(disabled_references)} disabled reference found.')

        logger.info('Start deleting disabled references...')
        for ref in disabled_references:
            db.session.delete(ref)

    db.session.commit()


def save_reference_in_database(process, usecase, all_database_references,
                               reference_basepath, type_reference, dm_pkl_exists, logger):
    # Check if reference is present in database and has correct information
    enabled_ref = 0
    new_ref = 0

    loaded_reference = list(filter(
        lambda ref: ref.reference_path == f'{process.process_path}.{process.name}.{usecase}' and
                    ref.reference_type == type_reference and
                    ref.process_id == process.id
        , all_database_references)
    )
    # Case reference exist in database
    if len(loaded_reference) > 0:
        if len(loaded_reference) == 1:
            existing_reference = loaded_reference[0]
        else:
            # Remove last entry in duplicate
            loaded_reference_sorted = sorted(loaded_reference, key=lambda ref: ref.id)
            for i in range(1, len(loaded_reference_sorted)):
                logger.info(f'Removed one duplicate entry for reference {loaded_reference_sorted[i].name} '
                            f'with process_id {loaded_reference_sorted[i].process_id}'
                            f'and id of duplicate {loaded_reference_sorted[i].id}')
                db.session.delete(loaded_reference_sorted[i])
            # Keep initial process
            existing_reference = loaded_reference_sorted[0]

        existing_reference.name = usecase
        existing_reference.process_id = process.id
        existing_reference.reference_type = type_reference
        existing_reference.disabled = False

        if dm_pkl_exists:
            # Update date in case regenerated by jenkins
            existing_reference.execution_status = ReferenceStudy.FINISHED
            existing_reference.creation_date = \
                datetime.fromtimestamp(stat(join(reference_basepath, process.process_path,
                                                 process.name, usecase, 'dm.pkl'))
                                       .st_mtime).astimezone(timezone.utc).replace(tzinfo=None)
        else:
            existing_reference.execution_status = ReferenceStudy.UNKNOWN
            existing_reference.creation_date = None

        enabled_ref += 1
        # Save in db updated ref
        db.session.add(existing_reference)

    else:
        # Create a new reference
        new_reference = ReferenceStudy()
        new_reference.name = usecase
        new_reference.reference_path = f'{process.process_path}.{process.name}.{usecase}'
        new_reference.process_id = process.id
        new_reference.reference_type = type_reference
        new_reference.creation_date = None
        new_reference.disabled = False

        if dm_pkl_exists:
            new_reference.execution_status = ReferenceStudy.FINISHED
            new_reference.creation_date = \
                datetime.fromtimestamp(stat(join(reference_basepath, process.process_path,
                                                 process.name, usecase, 'dm.pkl'))
                                       .st_mtime).astimezone(timezone.utc).replace(tzinfo=None)
        else:
            new_reference.execution_status = ReferenceStudy.UNKNOWN

        new_ref += 1
        enabled_ref += 1
        # Save in db new ref
        db.session.add(new_reference)

    return enabled_ref, new_ref


def is_usecase_data(process, usecase, logger):
    try:
        imported_module = import_module('.'.join([process.process_path, process.name, usecase]))
        imported_usecase = getattr(imported_module, 'Study')()

        if hasattr(imported_usecase, 'run_usecase') and not imported_usecase.run_usecase():
            return True
        else:
            return False

    except:
        logger.exception(f'Usecase {process.process_path}.{process.name}.{usecase} '
                         f'cannot be imported')
        return None
