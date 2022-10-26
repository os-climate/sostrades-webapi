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
from sos_trades_api.tests.controllers.unit_test_basic_config import DatabaseUnitTestConfiguration

"""
mode: python; py-indent-offset: 4; tab-width: 4; coding: utf-8
Test class for news procedures
"""


# pylint: disable=no-member
# pylint: disable=line-too-long


class TestNews(DatabaseUnitTestConfiguration):
    """ Test class for methods related to study controller
    """
    test_message = 'Test_news'
    test_user_id = None

    # New user
    username = 'user1_usrnme'
    firstname = 'user1_fn'
    lastname = 'user1_ln'
    username = 'user1_usrnme'
    password = 'user1_passwd'
    email = 'user1@airbus.com'
    user_profile_id = 2
    created_user_id = None

    def setUp(self):
        super().setUp()
        from sos_trades_api.models.database_models import User
        from sos_trades_api.controllers.sostrades_data.user_controller import add_user

        with DatabaseUnitTestConfiguration.app.app_context():
            test_user = User.query \
                .filter(User.username == self.username).first()
            if test_user is None:
                # Create a user_manager_test
                created_user, password_link = add_user(self.firstname, self.lastname, self.username,
                                                       self.password, self.email, self.user_profile_id)
                # Retrieve user_manager_test
                test_user = User.query \
                    .filter(User.username == created_user.username).first()
                self.assertEqual(
                    created_user, test_user, 'User created is not the same as the one found in the db.')

            self.assertIsNotNone(
                test_user, 'User test not found in database, check migrations')

            # Set user identifier
            self.test_user_id = test_user.id

    def test_get_all_news(self):
        from sos_trades_api.controllers.sostrades_data.news_controller import get_news
        with DatabaseUnitTestConfiguration.app.app_context():

            # Create news
            self.creation_news()

            # Retrieve news
            news = get_news()
            self.assertIsNotNone(news, 'Any news has been found in the database')

    def test_create_news(self):
        from sos_trades_api.models.database_models import News
        with DatabaseUnitTestConfiguration.app.app_context():
            # Create news
            news_created = self.creation_news()

            # Retrieve news that has been created
            test_news = News.query.filter(
                News.id == news_created.id).first()
            self.assertEqual(test_news.message, self.test_message, 'News not created')
            self.assertLessEqual(len(test_news.message), 300, 'The length of the message is greater than 300 characters')

    def test_update_news(self):
        from sos_trades_api.models.database_models import News
        from sos_trades_api.controllers.sostrades_data.news_controller import update_news
        with DatabaseUnitTestConfiguration.app.app_context():
            # Create news
            news_created = self.creation_news()
            new_message = 'test_new_message'

            # Update news
            update_news(new_message, news_created.id)
            updated_news = News.query.filter(
                News.id == news_created.id).first()

            self.assertEqual(updated_news.message, new_message, 'News not updated')
            self.assertLessEqual(len(new_message), 300, 'The length of the message is greater than 300 characters')

    def test_delete_news(self):
        from sos_trades_api.controllers.sostrades_data.news_controller import delete_news
        from sos_trades_api.models.database_models import News
        with DatabaseUnitTestConfiguration.app.app_context():
            # Create news
            news = self.creation_news()

            news_to_delete = News.query.filter(
                News.id == news.id).first()
            self.assertIsNotNone(news_to_delete, 'News to delete not found in database')

            # Delete news
            delete_news(news_to_delete.id)

            news_deleted = News.query.filter(
                News.id == self.test_news_id).first()
            self.assertIsNone(
                news_deleted, 'Error news deleted has be found in database')

    def creation_news(self):
        from sos_trades_api.controllers.sostrades_data.news_controller import create_news
        # Create test news
        news = create_news(self.test_message, self.test_user_id)
        self.test_news_id = news.id
        return news
