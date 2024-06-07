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
Test class for group management procedures
"""

from sos_trades_api.tests.controllers.unit_test_basic_config import (
    DatabaseUnitTestConfiguration,
)

# pylint: disable=no-member
# pylint: disable=line-too-long


class TestGroupManagemenent(DatabaseUnitTestConfiguration):
    """ Test class for methods related to group controller
    """

    @classmethod
    def setUpClass(cls):
        DatabaseUnitTestConfiguration.setUpClass()

    def setUp(self):
        super().setUp()
        from sos_trades_api.models.database_models import User
        with DatabaseUnitTestConfiguration.app.app_context():
            # Retrieve user_test
            test_user = User.query \
                .filter(User.username == User.STANDARD_USER_ACCOUNT_NAME).first()
            self.assertIsNotNone(
                test_user, 'Default user test not found in database, check migrations')
            self.test_user_id = test_user.id
            self.group_name = 'test_group'
            self.group_description = 'Group created for testing purpose'
            self.group_confidential = False

    def tearDown(self):
        super().tearDown()

    def test_01_get_all_groups(self):
        from sos_trades_api.controllers.sostrades_data.group_controller import (
            get_all_groups,
        )
        with DatabaseUnitTestConfiguration.app.app_context():
            all_groups = get_all_groups()
            self.assertIsNotNone(all_groups,
                                 'No group returned by get_all_groups().')

    def test_02_create_group(self):
        from sos_trades_api.controllers.sostrades_data.group_controller import (
            create_group,
        )
        from sos_trades_api.models.database_models import Group
        with DatabaseUnitTestConfiguration.app.app_context():
            create_group(self.test_user_id, self.group_name,
                         self.group_description, self.group_confidential)
            test_group = Group.query \
                .filter(Group.name == self.group_name).first()
            self.assertIsNotNone(test_group,
                                 'Created group not present in database.')

    def test_03_get_group_list(self):
        from sos_trades_api.controllers.sostrades_data.group_controller import (
            get_group_list,
        )
        with DatabaseUnitTestConfiguration.app.app_context():
            group_list = get_group_list(self.test_user_id)
            created_group_present = False
            for grp in group_list:
                if grp.group.name == self.group_name:
                    created_group_present = True
            self.assertTrue(created_group_present,
                            'Test group owned by test user not retrieved while looking for group list of test user')

    def test_04_delete_group(self):
        from sos_trades_api.controllers.sostrades_data.group_controller import (
            delete_group,
        )
        from sos_trades_api.models.database_models import Group
        with DatabaseUnitTestConfiguration.app.app_context():
            test_group = Group.query.filter(Group.name == self.group_name).first()
            test_group_id = test_group.id
            delete_group(test_group_id)
            is_group_deleted = Group.query \
                .filter(Group.id == test_group_id).first()
            self.assertIsNone(is_group_deleted,
                              'Test group still present in database after attempt to delete it.')
