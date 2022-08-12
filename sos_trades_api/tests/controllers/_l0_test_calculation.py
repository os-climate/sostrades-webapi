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
Test class for authentication procedures
"""

from sos_trades_api.tests.controllers.unit_test_basic_config import DatabaseUnitTestConfiguration
from importlib import import_module

# pylint: disable=no-member
# pylint: disable=line-too-long


class TestCalculation(DatabaseUnitTestConfiguration):
    """ Test class for methods related to calculation controller
    Default accounts are used to check those controller
    """
    test_repository_name = 'sos_trades_core.sos_processes.test'
    test_process_name = 'test_disc1_disc2_coupling'
    test_uc_name = 'usecase_coupling_2_disc_test'
    test_study_name = 'test_creation'
    test_user_id = None
    test_user_group_id = None

    @classmethod
    def setUpClass(cls):
        DatabaseUnitTestConfiguration.setUpClass()

        from sos_trades_api.server.base_server import database_process_setup
        database_process_setup()

    def setUp(self):
        super().setUp()

        from sos_trades_api.models.database_models import User, Group, Process, ProcessAccessUser, AccessRights

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

    def test_01_execute_calculation(self):
        from sos_trades_api.controllers.sostrades_main.study_case_controller import create_study_case
        import os
        import time
        from sos_trades_api.controllers.sostrades_data.calculation_controller import execute_calculation
        from sos_trades_api.models.database_models import StudyCaseDisciplineStatus, StudyCase, User, StudyCaseExecution
        from sos_trades_api.config import Config
        with DatabaseUnitTestConfiguration.app.app_context():
            reference_basepath = Config().reference_root_dir
            imported_module = import_module(
                '.'.join([self.test_repository_name, self.test_process_name, self.test_uc_name]))
            imported_usecase = getattr(
                imported_module, 'Study')()
            imported_usecase.set_dump_directory(
                reference_basepath)
            imported_usecase.load_data()
            imported_usecase.run(dump_study=True)
            imported_usecase.dump_data(imported_usecase.dump_directory)
            created_study = create_study_case(self.test_user_id,
                                              self.test_study_name,
                                              self.test_repository_name,
                                              self.test_process_name,
                                              self.test_user_group_id,
                                              self.test_uc_name,
                                              from_type='Reference')
            os.environ['SOS_TRADES_EXECUTION_STRATEGY'] = 'thread'
            execute_calculation(created_study.study_case.id,
                                User.STANDARD_USER_ACCOUNT_NAME)
            time.sleep(10.0)
            # Wait few seconds to be sure Object is created in db
            sc = StudyCase.query.filter(
                StudyCase.name == self.test_study_name).first()

            self.assertIsNotNone(sc.current_execution_id,
                                 'No study case execution created')

            sce = StudyCaseExecution.query.filter(
                StudyCaseExecution.id == sc.current_execution_id).first()
            self.assertIn(sce.execution_status,
                          [StudyCaseExecution.RUNNING, StudyCaseExecution.PENDING,
                           StudyCaseExecution.FINISHED, StudyCaseExecution.FAILED],
                          'Study case execution status not coherent')
            # sc_exec = StudyCaseDisciplineStatus.query\
            #     .filter(StudyCaseDisciplineStatus.study_case_id == sc.id).all()
            # self.assertGreater(
            # len(sc_exec), 0, 'StudyCaseDisciplineStatus not added into db')

    def test_02_calculation_status(self):
        from sos_trades_api.controllers.sostrades_data.calculation_controller import calculation_status
        from sos_trades_api.models.database_models import StudyCase, StudyCaseExecution
        with DatabaseUnitTestConfiguration.app.app_context():
            sc = StudyCase.query.filter(
                StudyCase.name == self.test_study_name).first()
            self.assertIsNotNone(sc.current_execution_id,
                                 'No study case execution created')
            sc_status = calculation_status(sc.id)

            sce = StudyCaseExecution.query.filter(
                StudyCaseExecution.id == sc.current_execution_id).first()
            self.assertEqual(sc_status.study_case_execution_status, sce.execution_status,
                             'Study case execution status not coherent')

    def test_03_get_calculation_dashboard(self):
        from sos_trades_api.controllers.sostrades_data.calculation_controller import get_calculation_dashboard,\
            execute_calculation
        from sos_trades_api.models.database_models import StudyCase, User, StudyCaseExecution
        import os
        import time
        with DatabaseUnitTestConfiguration.app.app_context():
            sc = StudyCase.query.filter(
                StudyCase.name == self.test_study_name).first()
            os.environ['SOS_TRADES_EXECUTION_STRATEGY'] = 'thread'
            execute_calculation(sc.id, User.STANDARD_USER_ACCOUNT_NAME)
            calc_dashboard = list(filter(lambda cd: cd.execution_status == StudyCaseExecution.RUNNING,
                                         get_calculation_dashboard()))
            self.assertTrue(len(calc_dashboard) >= 1,
                            'At least one study should be running.')
            self.assertEqual(calc_dashboard[0].study_case_id, sc.id,
                             f'Study running should be study with id { sc.id }')

            # Wait for process calculation end
            time.sleep(50.0)

    def test_04_stop_calculation(self):
        from sos_trades_api.controllers.sostrades_data.calculation_controller import calculation_status,\
            stop_calculation

        from sos_trades_api.models.database_models import StudyCase, StudyCaseExecution
        with DatabaseUnitTestConfiguration.app.app_context():
            sc = StudyCase.query.filter(
                StudyCase.name == self.test_study_name).first()
            stop_calculation(sc.id)

            sc_status = calculation_status(sc.id)
            self.assertEqual(sc_status.study_case_execution_status, StudyCaseExecution.STOPPED,
                             'Study case status not stopped while stop_calculation was called')
