'''
Copyright 2022 Airbus SAS
Modifications on 2024/06/07 Copyright 2024 Capgemini
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

from os.path import dirname, join

from flask_jwt_extended.config import config

from sos_trades_api import __file__ as sos_trades_api_file
from sos_trades_api.tests.controllers.unit_test_basic_config import (
    DatabaseUnitTestConfiguration,
)

"""
mode: python; py-indent-offset: 4; tab-width: 4; coding: utf-8
Test class for authentication procedures
"""


class TestAuthentication(DatabaseUnitTestConfiguration):
    """
    Test class for methods related to authentication controller
    Default accounts are used to check those controller
    """

    def setUp(self):
        super().setUp()

        # Retrieve standard user password (for test purpose)
        root_folder = dirname(sos_trades_api_file)
        secret_path = join(root_folder, "secret")
        secret_filepath = join(secret_path, "standardUserPassword")

        with open(secret_filepath) as f:
            self.standard_user_password = f.read()
            f.close()

    def test_login_succeeded(self):
        """
        Using a valid pair of credential, check authentication process.
        The test is done using a local test account attached to the application
        """
        from flask_jwt_extended import decode_token

        from sos_trades_api.controllers.sostrades_data.authentication_controller import (
            authenticate_user_standard,
        )
        from sos_trades_api.models.database_models import User

        with DatabaseUnitTestConfiguration.app.app_context():

            # Test access for test account
            jwt_access, _, _, _ = authenticate_user_standard(
                User.STANDARD_USER_ACCOUNT_NAME, self.standard_user_password)

            decoded_token = decode_token(jwt_access)

            self.assertEqual(decoded_token[config.identity_claim_key], User.STANDARD_USER_ACCOUNT_EMAIL,
                             "Test account user is not the same than the one stored into the jwt token")

    def test_login_failed(self):
        """
        Using invalid pair of credential, check that authentication process is failing
        """
        from sos_trades_api.controllers.sostrades_data.authentication_controller import (
            authenticate_user_standard,
        )
        from sos_trades_api.models.database_models import User
        from sos_trades_api.tools.authentication.authentication import (
            InvalidCredentials,
        )

        with DatabaseUnitTestConfiguration.app.app_context():

            # Test faillure on test account
            with self.assertRaises(InvalidCredentials):
                authenticate_user_standard(
                    User.STANDARD_USER_ACCOUNT_NAME, "bad password")

            # Test faillure on unknown account
            with self.assertRaises(InvalidCredentials):
                authenticate_user_standard(
                    "unknown_user", "bad password")
