'''
Copyright 2022 Airbus SAS
Modifications on 2023/11/07-2023/11/09 Copyright 2023 Capgemini

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

from sos_trades_api.tests.controllers.unit_test_basic_config import (
    DatabaseUnitTestConfiguration,
)

"""
Test class for user management procedures
"""


class TestUserManagemenent(DatabaseUnitTestConfiguration):
    """
    Test class for methods related to user controller
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
                test_user, "Default user test not found in database, check migrations")
            self.test_user_id = test_user.id
            self.test_user_name = test_user.username
            self.test_user_mail = test_user.email
            # Set field to create an user
            self.username = "user1_usrnme"
            self.firstname = "user1_fn"
            self.lastname = "user1_ln"
            self.username = "user1_usrnme"
            self.password = "user1_passwd"
            self.email = "user1@fake.com"
            self.user_profile_id = 2
            # Set field to update
            self.new_email = "mailhasbeenmodified@fake.com"

    def tearDown(self):
        super().tearDown()

    def test_01_get_user_list(self):
        # Database only got two users admin and test user
        # ensure the method get_user_list return one user and he is test user
        from sos_trades_api.controllers.sostrades_data.user_controller import (
            get_user_list,
        )
        with DatabaseUnitTestConfiguration.app.app_context():
            user_list = get_user_list()
            self.assertEqual(
                1, len(user_list), "User list returned is greater than 1, should only return test user")
            self.assertEqual(
                user_list[0].username, self.test_user_name, "User returned is not test user")

    def test_02_add_user(self):
        from sos_trades_api.controllers.sostrades_data.user_controller import add_user
        from sos_trades_api.models.database_models import User
        with DatabaseUnitTestConfiguration.app.app_context():
            created_user, password_link = add_user(self.firstname, self.lastname, self.username,
                                                   self.password, self.email, self.user_profile_id)
            created_user_from_db = User.query \
                .filter(User.username == self.username).first()
            self.assertEqual(
                created_user, created_user_from_db, "User created is not the same as the one found in the db.")
            # Ensure we can't create a second user with the same unique key
            # than the first one
            try:
                add_user(self.firstname, self.lastname, self.username,
                         self.password, self.email, self.user_profile_id)
                raise Exception("Can create user with duplicate unique key.")
            except:
                pass

    def test_03_update_user(self):
        from sos_trades_api.controllers.sostrades_data.user_controller import (
            update_user,
        )
        from sos_trades_api.models.database_models import User
        with DatabaseUnitTestConfiguration.app.app_context():
            user = User.query.filter(User.username == self.username).first()
            user_id = user.id
            update_user(user_id,  self.firstname,  self.lastname,
                        self.username,  self.new_email,  self.user_profile_id)
            updated_user = User.query \
                .filter(User.id == user_id).first()
            self.assertEqual(
                updated_user.email, self.new_email, "The field who should have been updated is not equal to the new value.")
            # Ensure we can't update an user with an existing unique key
            try:
                update_user(user_id,  self.firstname,  self.lastname,
                            self.username,  self.test_user_mail,  self.user_profile_id)
                raise Exception("Can update user with duplicate unique key.")
            except:
                pass

    def test_04_delete_user(self):
        from sos_trades_api.controllers.sostrades_data.user_controller import (
            delete_user,
        )
        from sos_trades_api.models.database_models import User
        with DatabaseUnitTestConfiguration.app.app_context():
            user = User.query.filter(User.username == self.username).first()
            user_id = user.id
            delete_user(user_id)
            deleted_user = User.query \
                .filter(User.id == user_id).first()
            self.assertIsNone(deleted_user,
                              "User has not been deleted successfully")

    def test_05_get_user_profile_list(self):
        from sos_trades_api.controllers.sostrades_data.user_controller import (
            get_user_profile_list,
        )
        with DatabaseUnitTestConfiguration.app.app_context():
            user_profile_list = get_user_profile_list()
            # Ensure the first one retrieved is not Admin profile and length is
            # >= 1
            self.assertNotEqual(len(user_profile_list), 0,
                                "Empty profile list")
