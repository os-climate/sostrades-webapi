'''
Copyright 2025 Capgemini

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

import os
import os.path
from builtins import classmethod
from time import sleep
import time


from sos_trades_api.tests.controllers.unit_test_basic_config import (
    DatabaseUnitTestConfiguration,
)

"""
Test class for study procedures
"""


class TestStudy(DatabaseUnitTestConfiguration):
    """
    Test class for methods related to study controller
    """

    test_repository_name = "sostrades_core.sos_processes.test"
    test_process_name = "test_disc1_disc2_coupling"
    test_usecase_name = "usecase_coupling_2_disc_test"
    test_study_name = "test_creation"
    test_study_id = None
    test_user_id = None
    test_user_group_id = None

    @classmethod
    def setUpClass(cls):
        DatabaseUnitTestConfiguration.setUpClass()

        from sos_trades_api.server.base_server import database_process_setup
        database_process_setup()

    def setUp(self):
        super().setUp()

        from sos_trades_api.controllers.sostrades_data.study_case_controller import (
            create_empty_study_case,
        )
        from sos_trades_api.controllers.sostrades_main.study_case_controller import (
            load_or_create_study_case,
        )
        from sos_trades_api.controllers.sostrades_data.reference_controller import generate_reference, get_generation_status
        from sos_trades_api.models.database_models import ReferenceStudy
        from sos_trades_api.models.database_models import (
            AccessRights,
            Group,
            Process,
            ProcessAccessUser,
            StudyCase,
            User,
        )
        from sos_trades_api.models.loaded_study_case import LoadStatus
        from sos_trades_api.server.base_server import study_case_cache

        with DatabaseUnitTestConfiguration.app.app_context():
            # Retrieve user_test
            test_user = User.query \
                .filter(User.username == User.STANDARD_USER_ACCOUNT_NAME).first()
            self.assertIsNotNone(
                test_user, "Default user test not found in database, check migrations")
            self.test_user_id = test_user.id
            # Retrieve all_group
            all_group = Group.query \
                .filter(Group.name == Group.ALL_USERS_GROUP).first()
            self.assertIsNotNone(
                all_group, 'Default "All group" group not found in database, check migrations')
            self.test_user_group_id = all_group.id
            # Retrieve test process id
            test_process = Process.query.filter(Process.name == self.test_process_name) \
                .filter(Process.process_path == self.test_repository_name).first()
            self.assertIsNotNone(
                test_process, 'Process "test_disc1_disc2_coupling" cannot be found in database')

            # Retrieve Manager access right
            manager_right = AccessRights.query.filter(
                AccessRights.access_right == AccessRights.MANAGER).first()
            self.assertIsNotNone(manager_right,
                                 "Default access right Manager cannot be found in database, check migrations")
            # Authorize user_test for process
            # Test if user already authorized
            process_access_user = ProcessAccessUser.query \
                .filter(ProcessAccessUser.process_id == test_process.id) \
                .filter(ProcessAccessUser.user_id == self.test_user_id) \
                .filter(ProcessAccessUser.right_id == manager_right.id).first()

            if process_access_user is None:
                new_user_test_auth = ProcessAccessUser()
                new_user_test_auth.user_id = self.test_user_id
                new_user_test_auth.process_id = test_process.id
                new_user_test_auth.right_id = manager_right.id

                DatabaseUnitTestConfiguration.db.session.add(
                    new_user_test_auth)
                DatabaseUnitTestConfiguration.db.session.commit()

            # generate the reference
            os.environ["SOS_TRADES_EXECUTION_STRATEGY"] = "thread"
            ref_id = generate_reference(self.test_repository_name, self.test_process_name, self.test_usecase_name, self.test_user_id)
            
            # check reference exists
            references = ReferenceStudy.query.filter(ReferenceStudy.id == ref_id).all()
            self.assertTrue(len(references) == 1)
            reference = references[0]

            # wait until the reference is generated
            while reference.execution_status in [
                    ReferenceStudy.RUNNING,
                    ReferenceStudy.PENDING]:
                time.sleep(10.0)
                reference = ReferenceStudy.query.filter(ReferenceStudy.id == ref_id).first()
                reference = get_generation_status(reference)

            self.assertTrue(reference.execution_status in [
                    ReferenceStudy.FINISHED,
                    ReferenceStudy.FAILED])


            # Create test studycase
            new_study_case = create_empty_study_case(self.test_user_id,
                                                     self.test_study_name,
                                                     self.test_repository_name,
                                                     self.test_process_name,
                                                     self.test_user_group_id,
                                                     self.test_usecase_name,
                                                     StudyCase.FROM_REFERENCE,
                                                     None,
                                                     None,
                                                     )

            self.test_study_id = new_study_case.id

            load_or_create_study_case( self.test_study_id)
            # wait study loaded
            stop = False
            counter = 0
            study_manager = study_case_cache.get_study_case(self.test_study_id, False)
            while not stop:
                if study_manager.load_status == LoadStatus.LOADED:
                    stop = True
                else:
                    if counter > 60:
                        self.assertTrue(
                            False, "test_study_id loading too long, check thread")
                    counter = counter + 1
                    sleep(1)

    def tearDown(self):
        super().tearDown()
        from sos_trades_api.models.database_models import StudyCase
        with DatabaseUnitTestConfiguration.app.app_context():
            DatabaseUnitTestConfiguration.db.session.query(StudyCase).delete()
            DatabaseUnitTestConfiguration.db.session.commit()

    def test_read_only_mode_access(self):
        from sos_trades_api.tools.loading.study_case_manager import StudyCaseManager
        from sos_trades_api.server.base_server import app
        with app.app_context():
            study_manager = StudyCaseManager(self.test_study_id)

            # check read only is created
            read_only_file = study_manager.get_read_only_file_path()
            self.assertTrue(read_only_file.endswith('.json'))
            self.assertTrue(study_manager.check_study_case_json_file_exists())
            read_only_content = study_manager.read_loaded_study_case_in_json_file()

            # check the structure of the read only mode
            # check studycase data
            self.assertTrue('study_case' in read_only_content)
            self.assertTrue('name' in read_only_content['study_case'])
            self.assertTrue('repository' in read_only_content['study_case'])
            self.assertTrue('process' in read_only_content['study_case'])
            self.assertTrue('treenode' in read_only_content)

            # check data management disciplines
            self.assertTrue('data_management_disciplines' in read_only_content['treenode']) 
            self.assertTrue(len(read_only_content['treenode']['data_management_disciplines']) > 0)
            self.assertTrue(self.test_study_name in read_only_content['treenode']['data_management_disciplines']) 
            self.assertTrue('disciplinary_inputs' in read_only_content['treenode']['data_management_disciplines'][self.test_study_name]) 
            self.assertTrue('disciplinary_outputs' in read_only_content['treenode']['data_management_disciplines'][self.test_study_name]) 
            self.assertTrue('numerical_parameters' in read_only_content['treenode']['data_management_disciplines'][self.test_study_name]) 
            self.assertTrue(len(read_only_content['treenode']['data_management_disciplines'][self.test_study_name]['numerical_parameters']) > 0)
            self.assertTrue('var_name' in list(read_only_content['treenode']['data_management_disciplines'][self.test_study_name]['numerical_parameters'].values())[0])
            self.assertTrue('variable_key' in list(read_only_content['treenode']['data_management_disciplines'][self.test_study_name]['numerical_parameters'].values())[0])
            self.assertTrue('value' in list(read_only_content['treenode']['data_management_disciplines'][self.test_study_name]['numerical_parameters'].values())[0])

            #check treenode
            self.assertTrue('model_name_full_path' in read_only_content['treenode'])  
            self.assertTrue('children' in read_only_content['treenode'])  
            self.assertTrue(len(read_only_content['treenode']['children']) > 0)
            self.assertTrue('model_name_full_path' in read_only_content['treenode']['children'][0])
            self.assertTrue('data_management_disciplines' in read_only_content['treenode']['children'][0])
            
            #check post_processings
            self.assertTrue('post_processings' in read_only_content)   


        