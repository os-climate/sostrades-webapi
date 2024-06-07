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

from builtins import classmethod

from sos_trades_api.tests.controllers.unit_test_basic_config import (
    DatabaseUnitTestConfiguration,
)

"""
Test class for processes procedures
"""


class TestProcess(DatabaseUnitTestConfiguration):
    """ Test class for methods related to process controller
    """

    @classmethod
    def setUpClass(cls):
        DatabaseUnitTestConfiguration.setUpClass()

        from sos_trades_api.server.base_server import database_process_setup
        database_process_setup()

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_loaded_process_in_database(self):
        """ Check that database contains default process to load
        """
        additional_repository_list = DatabaseUnitTestConfiguration.app.config[
            'SOS_TRADES_PROCESS_REPOSITORY']

        # Retrieve all process list
        from sostrades_core.sos_processes.processes_factory import SoSProcessFactory
        process_factory = SoSProcessFactory(
            additional_repository_list=additional_repository_list)

        # Get processes dictionary
        processes_dict = process_factory.get_processes_dict()

        # Retrieve all existing process from database
        with DatabaseUnitTestConfiguration.app.app_context():
            from sos_trades_api.models.database_models import Process
            all_database_processes = Process.query.all()

            for process_module, process_names in processes_dict.items():
                for process_name in process_names:

                    loaded_process = list(filter(
                        lambda process: process.process_path == process_module and process.name == process_name, all_database_processes))

                    self.assertEqual(len(
                        loaded_process), 1, 'Process is not present or cannot be present more than once')

    def test_standard_account_process_in_database(self):
        """ Check that all process are not accessible by the standard account without right access on processes.
        """

        with DatabaseUnitTestConfiguration.app.app_context():

            from sos_trades_api.models.database_models import User
            standard_account = User.query.filter(
                User.username == User.STANDARD_USER_ACCOUNT_NAME).first()

            from sos_trades_api.controllers.sostrades_data.process_controller import (
                api_get_processes_for_user,
            )
            standard_account_process = api_get_processes_for_user(
                standard_account)

            process_filtered = filter(
                lambda x: x.is_manager or x.is_contributor, standard_account_process)

            self.assertEqual(len((list(process_filtered))), 0,
                             'Some processes are accessible by the test account')
