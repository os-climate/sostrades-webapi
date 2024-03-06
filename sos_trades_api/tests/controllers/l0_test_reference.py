'''
Copyright 2022 Airbus SAS
Modifications on 2024/03/06 Copyright 2024 Capgemini


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
Test class for reference procedures
"""

from sos_trades_api.tests.controllers.unit_test_basic_config import DatabaseUnitTestConfiguration
from builtins import classmethod


# pylint: disable=no-member
# pylint: disable=line-too-long


class TestStudy(DatabaseUnitTestConfiguration):
    """ Test class for methods related to study controller
    """
    test_repository_name = 'sostrades_core.sos_processes.test'
    test_process_name = 'test_disc1_disc2_coupling'
    test_study_name = 'test_creation'
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

        from sos_trades_api.models.database_models import User, Group, Process, ProcessAccessUser, AccessRights, StudyCase
        from sos_trades_api.controllers.sostrades_main.study_case_controller import create_study_case
        from sos_trades_api.controllers.sostrades_data.study_case_controller import create_empty_study_case
        with DatabaseUnitTestConfiguration.app.app_context():
            # Retrieve user_test
            test_user = User.query \
                .filter(User.username == User.STANDARD_USER_ACCOUNT_NAME).first()
            self.assertIsNotNone(
                test_user, 'Default user test not found in database, check migrations')
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
                                 'Default access right Manager cannot be found in database, check migrations')
            # Authorize user_test for process
            # Test if user already authorized
            process_access_user = ProcessAccessUser.query\
                .filter(ProcessAccessUser.process_id == test_process.id)\
                .filter(ProcessAccessUser.user_id == self.test_user_id)\
                .filter(ProcessAccessUser.right_id == manager_right.id).first()

            if process_access_user is None:
                new_user_test_auth = ProcessAccessUser()
                new_user_test_auth.user_id = self.test_user_id
                new_user_test_auth.process_id = test_process.id
                new_user_test_auth.right_id = manager_right.id

                DatabaseUnitTestConfiguration.db.session.add(
                    new_user_test_auth)
                DatabaseUnitTestConfiguration.db.session.commit()

            # Create test studycase
            new_study_case = create_empty_study_case(self.test_user_id,
                                                     self.test_study_name,
                                                     self.test_repository_name,
                                                     self.test_process_name,
                                                     self.test_user_group_id,
                                                     'Empty Study',
                                                     StudyCase.FROM_REFERENCE
                                                     )

            created_study = create_study_case(self.test_user_id,
                                              new_study_case.id,
                                              None)

            self.test_study_id = created_study.study_case.id

    def tearDown(self):
        super().tearDown()
        from sos_trades_api.models.database_models import StudyCase
        with DatabaseUnitTestConfiguration.app.app_context():
            DatabaseUnitTestConfiguration.db.session.query(StudyCase).delete()
            DatabaseUnitTestConfiguration.db.session.commit()

    def test_get_all_references(self):
        from sos_trades_api.controllers.sostrades_data.reference_controller import get_all_references
        with DatabaseUnitTestConfiguration.app.app_context():
            try:
                references_list = get_all_references(self.test_user_id, None)
            except:
                self.assertTrue(False, 'Error while retrieving all references')
