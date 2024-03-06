'''
Copyright 2022 Airbus SAS
Modifications on 2023/10/13-2023/12/04 Copyright 2023 Capgemini

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
Test class for entity right procedures
"""


from sos_trades_api.tests.controllers.unit_test_basic_config import DatabaseUnitTestConfiguration


# pylint: disable=no-member
# pylint: disable=line-too-long


class TestEntityRight(DatabaseUnitTestConfiguration):
    """ Test class for methods related to calculation controller
    Default accounts & group and a created user / group are used to check those controller
    """
    test_repository_name = 'sostrades_core.sos_processes.test'
    test_process_name = 'test_disc1_disc2_coupling'
    test_study_name = 'test_creation'
    test_study_id = None
    test_user_id = None
    test_process_id = None

    default_group_id = None

    # New user
    username = 'user1_usrnme'
    firstname = 'user1_fn'
    lastname = 'user1_ln'
    username = 'user1_usrnme'
    password = 'user1_passwd'
    email = 'user@fake.com'
    user_profile_id = 2
    created_user_id = None


    # New group
    group_name = 'test_group'
    group_description = 'Group created for testing purpose'
    group_confidential = False
    created_group_id = None

    @classmethod
    def setUpClass(cls):
        DatabaseUnitTestConfiguration.setUpClass()
        from sos_trades_api.server.base_server import database_process_setup
        database_process_setup()

    def setUp(self):
        super().setUp()
        from sos_trades_api.models.database_models import User, Group, Process, ProcessAccessUser, AccessRights, \
            StudyCase
        from sos_trades_api.controllers.sostrades_main.study_case_controller import create_study_case
        from sos_trades_api.controllers.sostrades_data.study_case_controller import create_empty_study_case
        with DatabaseUnitTestConfiguration.app.app_context():
            # Retrieve user_test
            test_user = User.query \
                .filter(User.username == User.STANDARD_USER_ACCOUNT_NAME).first()
            self.assertIsNotNone(
                test_user, 'Default user test not found in database, check migrations')
            self.test_user_id = test_user.id
            default_group = Group.query \
                .filter(Group.is_default_applicative_group).first()
            self.default_group_id = default_group.id

            # Retrieve test process id

            test_process = Process.query.filter(Process.name == self.test_process_name) \
                .filter(Process.process_path == self.test_repository_name).first()
            self.assertIsNotNone(
                test_process, 'Process "test_disc1_disc2_coupling" cannot be found in database')
            self.test_process_id = test_process.id

            # Retrieve Manager access right
            manager_right = AccessRights.query.filter(
                AccessRights.access_right == AccessRights.MANAGER).first()
            self.assertIsNotNone(manager_right,
                                 'Default access right Manager cannot be found in database, check migrations')

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

            # Create a new study if it does not already exist
            create_new_study = True
            # Retrieve all studies with the targeted group
            all_studies = StudyCase.query.filter(StudyCase.group_id == default_group.id).all()
            if all_studies is not None:
                for study in all_studies:
                    if study.name == self.test_study_name:
                        self.test_study_id = study.id
                        create_new_study = False

            if create_new_study:
                # Create test study_case
                new_study_case = create_empty_study_case(self.test_user_id,
                                                         self.test_study_name,
                                                         self.test_repository_name,
                                                         self.test_process_name,
                                                         self.default_group_id,
                                                         'Empty Study',
                                                         StudyCase.FROM_REFERENCE)

                self.test_study_id = new_study_case.id

                created_study = create_study_case(self.test_user_id,
                                                  self.test_study_id,
                                                  None)

                self.test_study_id = created_study.study_case.id

    def tearDown(self):
        super().tearDown()

    def test_01_apply_entities_changes(self):
        from sos_trades_api.controllers.sostrades_data.entity_right_controller import apply_entities_changes
        from sos_trades_api.models.database_models import GroupAccessUser, AccessRights
        from sos_trades_api.controllers.sostrades_data.user_controller import add_user
        from sos_trades_api.controllers.sostrades_data.group_controller import create_group
        with DatabaseUnitTestConfiguration.app.app_context():
            # Create user and group
            created_group = create_group(
                self.test_user_id, self.group_name, self.group_description, self.group_confidential)
            created_user, password_link = add_user(self.firstname, self.lastname, self.username,
                                                   self.password, self.email, self.user_profile_id)
            # Give membership right to created user to created group
            member_rights = AccessRights.query.filter(
                AccessRights.access_right == AccessRights.MEMBER).first()
            member_rights_id = member_rights.id
            entities_rights = {"resourceId": created_group.id,
                               "resourceType": "group",
                               "availableRights":
                                   [],
                               "entitiesRights":
                                   [{"id": -1, "entityType": "user",
                                     "entityObject":
                                         {"id": created_user.id},
                                     "selectedRight": member_rights_id,
                                     "isLocked": False,
                                     "oldRight": None}]}
            apply_entities_changes(
                self.test_user_id, self.user_profile_id, entities_rights)
            group_access_user = GroupAccessUser.query \
                .filter(GroupAccessUser.group_id == created_group.id) \
                .filter(GroupAccessUser.user_id == created_user.id).first()

            self.assertEqual(group_access_user.right_id, member_rights_id,
                             'Right not coherent')

    def test_02_get_study_case_entities_rights(self):
        from sos_trades_api.controllers.sostrades_data.entity_right_controller import get_study_case_entities_rights
        from sos_trades_api.models.entity_rights import EntityType
        with DatabaseUnitTestConfiguration.app.app_context():
            study_case_entities_right = get_study_case_entities_rights(
                self.test_user_id, self.test_study_id)
            for ent_r in study_case_entities_right.entity.entities_rights:
                if ent_r.entity_type == EntityType.USER:
                    self.assertEqual(ent_r.entity_object.id, self.test_user_id,
                                     'User right for study case created not coherent, other user than test user has access right to the study')
                if ent_r.entity_type == EntityType.GROUP:
                    self.assertEqual(ent_r.entity_object.id, self.default_group_id,
                                     'Group right for study case created not coherent, other group than default group has access right to the study')

    def test_03_get_process_entities_rights(self):
        from sos_trades_api.controllers.sostrades_data.entity_right_controller import get_process_entities_rights
        from sos_trades_api.models.entity_rights import EntityType
        with DatabaseUnitTestConfiguration.app.app_context():
            process_entities_right = get_process_entities_rights(
                self.test_user_id, self.user_profile_id, self.test_process_id)
            # Only test user (granted in setup) and SoSTrades Dev group should
            # have access to this resource
            for ent_r in process_entities_right.entity.entities_rights:
                if ent_r.entity_type == EntityType.USER:
                    self.assertEqual(ent_r.entity_object.id, self.test_user_id,
                                     'User right for study case created not coherent, other user than test user has access right to the study')
                if ent_r.entity_type == EntityType.GROUP:
                    self.assertEqual(ent_r.entity_object.id, self.default_group_id,
                                     'Group right for study case created not coherent, other group than SoSTrades Dev group has access right to the study')

    def test_04_get_group_entities_rights(self):
        # Created group should have 2 entity right, one for test _user, one for
        # created user
        from sos_trades_api.controllers.sostrades_data.entity_right_controller import get_group_entities_rights
        from sos_trades_api.models.database_models import AccessRights
        from sos_trades_api.models.entity_rights import EntityType
        from sos_trades_api.models.database_models import Group, User
        with DatabaseUnitTestConfiguration.app.app_context():
            member_rights = AccessRights.query.filter(
                AccessRights.access_right == AccessRights.MEMBER).first()
            owner_right = AccessRights.query.filter(
                AccessRights.access_right == AccessRights.OWNER).first()
            group_id = (Group.query
                        .filter(Group.name == self.group_name).first()).id
            created_user_id = (User.query
                               .filter(User.username == self.username).first()).id
            group_entities_rights = get_group_entities_rights(
                self.test_user_id, group_id)
            for ent_r in group_entities_rights.entity.entities_rights:
                if ent_r.entity_type == EntityType.USER:
                    self.assertIn(ent_r.entity_object.id, [self.test_user_id, created_user_id],
                                  'User right for created group not coherent, other user than test user/ created user has access right to the study')
                    if ent_r.entity_object.id == self.test_user_id:
                        self.assertEqual(ent_r.selected_right, owner_right.id,
                                         'Test_user is not owner of group he created')
                    elif ent_r.entity_object.id == created_user_id:
                        self.assertEqual(ent_r.selected_right, member_rights.id,
                                         'created_user is not member of group he has been added as member')
                if ent_r.entity_type == EntityType.GROUP:
                    self.assertTrue(False,
                                    'Group right for created group created not coherent, no group should have access to this group')

    def test_05_verify_user_authorised_for_resource(self):
        from sos_trades_api.controllers.sostrades_data.entity_right_controller import \
            verify_user_authorised_for_resource
        from sos_trades_api.models.database_models import Group, User, UserProfile
        from sos_trades_api.tools.right_management.access_right import has_access_to, APP_MODULE_EXECUTION
        with DatabaseUnitTestConfiguration.app.app_context():
            group_id = (Group.query
                        .filter(Group.name == self.group_name).first()).id
            created_user_id = (User.query
                               .filter(User.username == self.username).first()).id
            entities_rights_group = {"resourceId": group_id,
                                     "resourceType": "group",
                                     }
            entities_rights_study_case = {"resourceId": self.test_study_id,
                                          "resourceType": "study_case",
                                          }
            entities_rights_process = {"resourceId": self.test_process_id,
                                       "resourceType": "process",
                                       }
            # Created user should have access to nothing
            created_user_authorised_group = verify_user_authorised_for_resource(
                created_user_id, self.user_profile_id, entities_rights_group)
            created_user_authorised_sc = verify_user_authorised_for_resource(
                created_user_id, self.user_profile_id, entities_rights_study_case)
            self.assertFalse(created_user_authorised_group,
                             'the user created must not be authorized for the resource created_group')
            self.assertFalse(created_user_authorised_sc,
                             'the user created must not be authorized for the resource study case')
            # Test user should have access to everything
            test_user_authorised_group = verify_user_authorised_for_resource(
                self.test_user_id, self.user_profile_id, entities_rights_group)
            test_user_authorised_sc = verify_user_authorised_for_resource(
                self.test_user_id, self.user_profile_id, entities_rights_study_case)
            test_user_authorised_process = verify_user_authorised_for_resource(
                self.test_user_id, self.user_profile_id, entities_rights_study_case)
            self.assertTrue(test_user_authorised_group,
                            'test user must be authorized for the resource created_group')
            self.assertTrue(test_user_authorised_sc,
                            'test user must be authorized for the resource study case')
            self.assertTrue(test_user_authorised_process,
                            'test user must not be authorized for the resource process')

            # check user is authorized for execution mode
            profile_no_execution = UserProfile.query.filter(
                UserProfile.name == UserProfile.STUDY_USER_NO_EXECUTION).first()
            if profile_no_execution is not None:
                
                #retrieve standard user
                standard_test_user = User.query.filter(User.username == User.STANDARD_USER_ACCOUNT_NAME).first()
                
                # check execution rights  
                has_right = has_access_to(profile_no_execution.id, APP_MODULE_EXECUTION)
                self.assertFalse(has_right,'this profile should have no execution right')
                
                has_right = has_access_to(standard_test_user.user_profile_id, APP_MODULE_EXECUTION)
                self.assertTrue(has_right,'the standard user test profile should have execution right')


    def test_06_change_process_source_rights(self):
        from sos_trades_api.models.database_models import ProcessAccessUser, User, Group, AccessRights
        from sos_trades_api.controllers.sostrades_data.entity_right_controller import apply_entities_changes
        with DatabaseUnitTestConfiguration.app.app_context():
            group_id = (Group.query
                        .filter(Group.name == self.group_name).first()).id
            created_user_id = (User.query
                               .filter(User.username == self.username).first()).id
            # get process access user of test_user
            process_access_user = ProcessAccessUser.query \
                .filter(ProcessAccessUser.process_id == self.test_process_id) \
                .filter(ProcessAccessUser.user_id == self.test_user_id).first()
            self.assertIsNotNone(process_access_user,
                                 'ProcessAccessUser not found')
            # check processAccessUser source is USER
            self.assertEqual(process_access_user.source, ProcessAccessUser.SOURCE_USER,
                             'source not initialized to USER')

            # change processAccessUser source to FILE
            process_access_user.source = ProcessAccessUser.SOURCE_FILE
            DatabaseUnitTestConfiguration.db.session.commit()

            # change rights with API
            # Give contributor right to created user to process
            member_rights = AccessRights.query.filter(
                AccessRights.access_right == AccessRights.CONTRIBUTOR).first()
            member_rights_id = member_rights.id
            entities_rights = {"resourceId": self.test_process_id,
                               "resourceType": "process",
                               "availableRights":
                                   [],
                               "entitiesRights":
                                   [{"id": process_access_user.id, "entityType": "user",
                                     "entityObject":
                                         {"id": created_user_id},
                                     "selectedRight": member_rights_id,
                                     "isLocked": False,
                                     "oldRight": None}]}
            apply_entities_changes(
                self.test_user_id, self.user_profile_id, entities_rights)
            process_access_user = ProcessAccessUser.query \
                .filter(ProcessAccessUser.process_id == self.test_process_id) \
                .filter(ProcessAccessUser.user_id == self.test_user_id).first()

            self.assertEqual(process_access_user.source, ProcessAccessUser.SOURCE_USER,
                             'source not set to USER')
    
