'''
Copyright 2024 Capgemini

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

import argparse
import os
from os.path import dirname, join
from time import sleep


def test_reload_study_case(study_id, user_id ):
    """
    Load a study and do a reload 10 times to see the memory flow
    """
    from memory_profiler import memory_usage

    from sos_trades_api.controllers.sostrades_main.study_case_controller import (
        load_study_case,
    )
    from sos_trades_api.models.database_models import AccessRights, StudyCase
    from sos_trades_api.models.loaded_study_case import LoadStatus
    from sos_trades_api.server.base_server import app, study_case_cache

    with app.app_context():
        study_test = StudyCase.query.filter(StudyCase.id == study_id).first()
        
        study_manager = study_case_cache.get_study_case(study_test.id, False)

        mem_before = memory_usage()[0]
        app.logger.info(f"Memory before first loading: {mem_before} MB")
        loaded_study = load_study_case(
            study_test.id, AccessRights.MANAGER, user_id)

        #  wait until study was updated (thread behind)
        stop = False
        counter = 0

        while not stop:
            if study_manager.load_status == LoadStatus.LOADED:
                stop = True
            else:
                if counter > 360:
                    raise Exception( "test_update_study_parameters update study parameter too long, check thread")
                counter = counter + 1
                sleep(1)
        
        # reload 10 times
        for i in range(0,10):
            mem_after = memory_usage()[0]
            app.logger.info(f"Memory before {i} reloading: {mem_after} MB")
            loaded_study = load_study_case(
                study_test.id, AccessRights.MANAGER, user_id, reload=True)
            
            while not stop:
                if study_manager.load_status == LoadStatus.LOADED:
                    stop = True
                else:
                    if counter > 360:
                        raise Exception("test_update_study_parameters update study parameter too long, check thread")
                    counter = counter + 1
                    sleep(1)
            mem_after_reload = memory_usage()[0]
            app.logger.info(f"Memory after reload loading: {mem_after_reload} MB")
            app.logger.info(f"Memory used by this block: {mem_after_reload - mem_after} MB")
            sleep(10)

if __name__=='__main__':
    from dotenv import load_dotenv
    if os.environ.get("SOS_TRADES_SERVER_CONFIGURATION") is None:
        dotenv_path = join(dirname(__file__),"..", "..", "..", ".flaskenv")
        print(dotenv_path)
        load_dotenv(dotenv_path)


    
    parser = argparse.ArgumentParser(description='test memory')

    parser.add_argument(
        '--user_id',
        nargs='?',
        type=int
    )

    parser.add_argument(
        '--study_id', nargs='?', type=int, help='Generate the given reference'
    )

    args = vars(parser.parse_args())

    test_reload_study_case(args['study_id'],args['user_id'])