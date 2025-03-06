'''
Copyright 2022 Airbus SAS
Modifications on 2023/09/01-2023/11/23 Copyright 2023 Capgemini

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
    #test_clear_error_process_name = 'test_sellar_opt'
    test_clear_error_process_name = "test_sellar_opt_discopt"
    test_csv_process_name = "test_csv_data"
    test_study_name = "test_creation"
    test_study_csv_name = "test_csv"
    test_study_clear_error_name = "test_clear_error"
    test_study_id = None
    test_study_csv_id = None
    test_study_clear_error_id = None
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
        from sos_trades_api.models.database_models import (
            AccessRights,
            Group,
            Process,
            ProcessAccessUser,
            StudyCase,
            User,
        )
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
            # Retrieve test process id
            test_csv_process = Process.query.filter(Process.name == self.test_csv_process_name) \
                .filter(Process.process_path == self.test_repository_name).first()
            self.assertIsNotNone(
                test_csv_process, 'Process "test_csv_data" cannot be found in database')
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

            # Create test studycase
            new_study_case = create_empty_study_case(self.test_user_id,
                                                     self.test_study_name,
                                                     self.test_repository_name,
                                                     self.test_process_name,
                                                     self.test_user_group_id,
                                                     "Empty Study",
                                                     StudyCase.FROM_REFERENCE,
                                                     None,
                                                     None,
                                                     )

            self.test_study_id = new_study_case.id

            load_or_create_study_case( self.test_study_id)

            # Create test csv studycase
            new_study_case_csv = create_empty_study_case(self.test_user_id,
                                                         self.test_study_csv_name,
                                                         self.test_repository_name,
                                                         self.test_csv_process_name,
                                                         self.test_user_group_id,
                                                         "Empty Study",
                                                         StudyCase.FROM_REFERENCE,
                                                     None,
                                                     None,
                                                         )

            self.test_study_csv_id = new_study_case_csv.id

            load_or_create_study_case(self.test_study_csv_id)

            # Create  test clear_error studycase
            new_study_case_clear_error = create_empty_study_case(self.test_user_id,
                                                                 self.test_study_clear_error_name,
                                                                 self.test_repository_name,
                                                                 self.test_clear_error_process_name,
                                                                 self.test_user_group_id,
                                                                 "Empty Study",
                                                                 StudyCase.FROM_REFERENCE,
                                                     None,
                                                     None,
                                                                 )

            self.test_study_clear_error_id = new_study_case_clear_error.id

            load_or_create_study_case(self.test_study_clear_error_id)

    def tearDown(self):
        super().tearDown()
        from sos_trades_api.models.database_models import StudyCase
        with DatabaseUnitTestConfiguration.app.app_context():
            DatabaseUnitTestConfiguration.db.session.query(StudyCase).delete()
            DatabaseUnitTestConfiguration.db.session.commit()

    def test_create_study_case(self):
        from sos_trades_api.models.database_models import StudyCase
        with DatabaseUnitTestConfiguration.app.app_context():
            new_created_study = StudyCase.query.filter(
                StudyCase.id == self.test_study_id).first()
            self.assertEqual(new_created_study.name, self.test_study_name,
                             "Created study case name does not match, test set up name used")
            self.assertEqual(new_created_study.process, self.test_process_name,
                             "Created study case process does not match, test set up process name used")
            self.assertEqual(new_created_study.repository, self.test_repository_name,
                             "Created study case repository does not match, test set up repository name used")

    def test_get_user_shared_study_case(self):
        from sos_trades_api.controllers.sostrades_data.study_case_controller import (
            get_user_shared_study_case,
        )
        with DatabaseUnitTestConfiguration.app.app_context():
            user_shared_study_cases = get_user_shared_study_case(
                self.test_user_id)
            # User has access only to the 2 created study case in test set up
            # First created study test_disc1_disc2_coupling
            study_test_disc1_disc2_coupling = list(filter(lambda std: std.name == self.test_study_name
                                                          and std.process == self.test_process_name
                                                          and std.repository == self.test_repository_name, user_shared_study_cases))
            self.assertIsNotNone(study_test_disc1_disc2_coupling[0],
                                 "Created study case test_disc1_disc2_coupling cannot be found in database")

            # Secondly created study case test_csv_data
            study_test_csv = list(filter(lambda std: std.name == self.test_study_csv_name
                                         and std.process == self.test_csv_process_name
                                         and std.repository == self.test_repository_name, user_shared_study_cases))
            self.assertIsNotNone(study_test_csv[0],
                                 "Created study case test_csv_data cannot be found in database")

            # thirdly created study case test_csv_data
            study_test_clear_error = list(filter(lambda std: std.name == self.test_study_clear_error_name
                                                 and std.process == self.test_clear_error_process_name
                                                 and std.repository == self.test_repository_name, user_shared_study_cases))
            self.assertIsNotNone(study_test_clear_error[0],
                                 "Created study case test_clear_error cannot be found in database")

            # Checking only 3 study cases
            self.assertEqual(len(user_shared_study_cases), 3,
                             "User study case list does not match, study case list created and shared in test")

    def test_load_study_case(self):
        from sos_trades_api.controllers.sostrades_main.study_case_controller import (
            load_study_case,
        )
        from sos_trades_api.models.database_models import StudyCase
        from sos_trades_api.models.loaded_study_case import LoadStatus
        from sos_trades_api.server.base_server import study_case_cache

        with DatabaseUnitTestConfiguration.app.app_context():
            study_test = StudyCase.query.filter(
                StudyCase.name == self.test_study_name).first()
            self.assertIsNotNone(
                study_test, "Unable to retrieve study case created for test")

            study_manager = study_case_cache.get_study_case(study_test.id, False)

            load_study_case(study_test.id)

            #  wait until study was updated (thread behind)
            stop = False
            counter = 0

            while not stop:
                if study_manager.load_status == LoadStatus.LOADED:
                    stop = True
                else:
                    if counter > 60:
                        self.assertTrue(
                            False, "test_update_study_parameters update study parameter too long, check thread")
                    counter = counter + 1
                    sleep(1)

            self.assertEqual(study_test.name, self.test_study_name,
                             "Created study case name does not match, test set up name used")
            self.assertEqual(study_test.process, self.test_process_name,
                             "Created study case process does not match, test set up process name used")
            self.assertEqual(study_test.repository, self.test_repository_name,
                             "Created study case repository does not match, test set up repository name used")

    def test_study_case_log(self):
        from sos_trades_api.models.database_models import (
            StudyCase,
            StudyCaseLog,
        )

        with DatabaseUnitTestConfiguration.app.app_context():
            study_test = StudyCase.query.filter(
                StudyCase.name == self.test_study_name).first()
            self.assertIsNotNone(
                study_test, "Unable to retrieve study case created for test")

            # check that logs are created
            self.assertNotEqual(len(StudyCaseLog.query
                                    .filter(StudyCaseLog.study_case_id == study_test.id)
                                    .all()), 0)

    def test_copy_study_case(self):
        from sos_trades_api.controllers.sostrades_data.study_case_controller import (
            create_empty_study_case,
        )
        from sos_trades_api.controllers.sostrades_main.study_case_controller import (
            load_or_create_study_case,
        )
        from sos_trades_api.models.database_models import StudyCase
        with DatabaseUnitTestConfiguration.app.app_context():
            study_test = StudyCase.query.filter(
                StudyCase.name == self.test_study_name).first()
            self.assertIsNotNone(
                study_test, "Unable to retrieve study case created for test")
            study_copy_name = "test_study_copy"

            new_study_case = create_empty_study_case(self.test_user_id,
                                                     study_copy_name,
                                                     study_test.repository,
                                                     study_test.process,
                                                     self.test_user_group_id,
                                                     str(study_test.id),
                                                     StudyCase.FROM_STUDYCASE,
                                                     None,
                                                     None,
                                                     )

            load_or_create_study_case(new_study_case.id)

            study_case_copied = StudyCase.query.filter(
                StudyCase.name == study_copy_name).first()
            self.assertEqual(study_case_copied.process, self.test_process_name,
                             "Copied study case process does not match, test set up process name used")
            self.assertEqual(study_case_copied.repository, self.test_repository_name,
                             "Copied study case repository does not match, test set up repository name used")
            
            # Add some delay for the execution to end to avoid issues in logs after database cleanup
            sleep(20)

    def test_update_study_parameters(self):
        from sos_trades_api.controllers.sostrades_main.study_case_controller import (
            update_study_parameters,
        )
        from sos_trades_api.models.database_models import StudyCase, User
        from sos_trades_api.models.loaded_study_case import LoadStatus
        from sos_trades_api.server.base_server import study_case_cache
        with DatabaseUnitTestConfiguration.app.app_context():
            study_test = StudyCase.query.filter(
                StudyCase.name == self.test_study_name).first()
            self.assertIsNotNone(
                study_test, "Unable to retrieve study case created for test")

            user_test = User.query.filter(User.id == self.test_user_id).first()
            self.assertIsNotNone(
                user_test, "Unable to retrieve user_test, check migrations")

            initial_modification_date = study_test.modification_date
            parameters_update_list = [
                {"variableId": f"{study_test.name}.Disc1.a",
                 "variableType": "float",
                 "changeType": "scalar",
                 "newValue": 10,
                 "oldValue": 5,
                 "namespace": f"{study_test.name}",
                 "discipline": "Disc1",
                 "lastModified": "2021-01-11T13:51:26.118Z", "id": None, "author": None},
            ]
            columns_to_delete = []

            study_manager = study_case_cache.get_study_case(study_test.id, False)

            # Wait in order to force modification date change (test failed on
            # too performant machine)
            sleep(2)

            # updating study case
            update_study_parameters(
                study_test.id, user_test, None, None, parameters_update_list, columns_to_delete)

        #  wait until study was updated (thread behind)
        stop = False
        counter = 0

        while not stop:
            if study_manager.load_status == LoadStatus.LOADED:
                stop = True
            else:
                if counter > 60:
                    self.assertTrue(
                        False, "test_update_study_parameters update study parameter too long, check thread")
                counter = counter + 1
                sleep(1)

        with DatabaseUnitTestConfiguration.app.app_context():

            # Checking test study modification date
            study_test_updated = StudyCase.query.filter(
                StudyCase.name == self.test_study_name).first()
            self.assertIsNotNone(
                study_test_updated, "Unable to retrieve study case created and updated for test")
            last_modification_date = study_test_updated.modification_date
            # self.assertNotEqual(initial_modification_date, last_modification_date,
            #                    'Modification date cannot be the same as the one at creation')

    def test_update_study_parameters_csv_data(self):
        from os.path import dirname, join

        import numpy as np
        import pandas as pd
        from werkzeug.datastructures import FileStorage

        from sos_trades_api.controllers.sostrades_main.study_case_controller import (
            update_study_parameters,
        )
        from sos_trades_api.models.database_models import StudyCase, User
        from sos_trades_api.models.loaded_study_case import LoadStatus
        from sos_trades_api.server.base_server import study_case_cache
        from sos_trades_api.tests import data

        with DatabaseUnitTestConfiguration.app.app_context():
            study_csv_test = StudyCase.query.filter(
                StudyCase.name == self.test_study_csv_name).first()
            self.assertIsNotNone(
                study_csv_test, "Unable to retrieve study case csv created for test")

            user_test = User.query.filter(User.id == self.test_user_id).first()
            self.assertIsNotNone(
                user_test, "Unable to retrieve user_test, check migrations")

            study_manager = study_case_cache.get_study_case(study_csv_test.id, False)

            # Wait in order to force modification date change (test failed on
            # too performant machine)
            sleep(2)

            # Declaration of objects to test
            array_mixed_types = np.array(("TEXT", None, "", 1, 1), dtype="O")
            dict_mixed_types = {"a": "", "b": None,
                                "c": [1, None, 3], "d": "test"}
            dataframe_mix_types = pd.DataFrame(
                {"a": [1, None, 3], "b": 40.0, "c": ["abc", "", None]})
            dict_as_dict_dataframe_types = \
                {
                    "dict_key_1": pd.DataFrame(
                        {
                            "col1": ["col_1_value_1", "col_1_value_2", "col_1_value_3", "col_1_value_4",
                                     "col_1_value_5", "col_1_value_6", "col_1_value_7", "col_1_value_8",
                                     "col_1_value_9"],
                            "col2": [3001.0, 3002.0, 3003.0, 3004.0, 3005.0, 3006.0, 3008.0, 3007.0, 3009.0],
                        },
                    ),
                    "dict_key_3": pd.DataFrame(
                        {
                            "col1": ["col_1_value_10", "col_1_value_11", "col_1_value_12", "col_1_value_13",
                                     "col_1_value_14", "col_1_value_15", "col_1_value_16", "col_1_value_17",
                                     "col_1_value_18", "col_1_value_19", "col_1_value_20", "col_1_value_21",
                                     "col_1_value_22", "col_1_value_23", "col_1_value_24", "col_1_value_25",
                                     "col_1_value_26", "col_1_value_27", "col_1_value_28"],
                            "col2": [3008.0, 3001.0, 3002.0, 3000.0, 3003.0, 3006.0, 3009.0, 3008.0, 3007.0, 3005.0,
                                     3004.0, 3002.0, 3001.0, 3005.0, 3003.0, 3006.0, 3004.0, 3008.0, 3009.0],
                        },
                    ),
                }
            # Array ---------------------------------------
            array_path = join(dirname(data.__file__), "array_mix_types.csv")
            array_file = open(array_path, "rb")
            array_fs = FileStorage(array_file)
            # Dict ---------------------------------------
            dict_path = join(dirname(data.__file__), "dict_mix_types.csv")
            dict_file = open(dict_path, "rb")
            dict_fs = FileStorage(dict_file)
            # Dataframe ---------------------------------------
            dataframe_path = join(dirname(data.__file__),
                                  "dataframe_mix_types.csv")
            dataframe_file = open(dataframe_path, "rb")
            dataframe_fs = FileStorage(dataframe_file)
            # Dict as Dict of dataframe ---------------------------------------
            # type dict
            # subtype_descriptor: {'dict': 'dataframe'}
            dict_as_dict_dataframe_path = join(dirname(data.__file__),
                                               "dict_as_dict_dataframe.csv")
            dict_as_dict_dataframe_file = open(
                dict_as_dict_dataframe_path, "rb")
            dict_as_dict_dataframe_fs = FileStorage(
                dict_as_dict_dataframe_file)

            file_info = {
                array_path: {"variable_id": f"{self.test_study_csv_name}.array_mix_types",
                             "discipline": "Data", "namespace": f"{self.test_study_csv_name}"},
                dict_path: {"variable_id": f"{self.test_study_csv_name}.dict_mix_types",
                            "discipline": "Data", "namespace": f"{self.test_study_csv_name}"},
                dataframe_path: {"variable_id": f"{self.test_study_csv_name}.dataframe_mix_types",
                                 "discipline": "Data", "namespace": f"{self.test_study_csv_name}"},
                dict_as_dict_dataframe_path: {"variable_id": f"{self.test_study_csv_name}.dict_as_dict_dataframe",
                                              "discipline": "Data", "namespace": f"{self.test_study_csv_name}"},

            }
            files_list = [array_fs, dict_fs,
                          dataframe_fs, dict_as_dict_dataframe_fs]
            columns_to_delete = []
            # updating study case
            update_study_parameters(
                study_csv_test.id, user_test, files_list, file_info, [], columns_to_delete)

        #  wait until study was updated (thread behind)
        stop = False
        counter = 0

        while not stop:
            if study_manager.load_status == LoadStatus.LOADED:
                stop = True
            else:
                if counter > 60:
                    self.assertTrue(
                        False, "test_csv_update_study_parameters update study parameter too long, check thread")
                counter = counter + 1
                sleep(1)

        with DatabaseUnitTestConfiguration.app.app_context():
            study_dm = study_manager.execution_engine.dm.convert_data_dict_with_full_name()
            dm_array = np.array(
                study_dm[f"{self.test_study_csv_name}.array_mix_types"]["value"])
            dm_dict = study_dm[f"{self.test_study_csv_name}.dict_mix_types"]["value"]
            dm_dataframe = study_dm[f"{self.test_study_csv_name}.dataframe_mix_types"]["value"]
            dm_dict_as_dict_dataframe = study_dm[f"{self.test_study_csv_name}.dict_as_dict_dataframe"]["value"]

            self.assertTrue(np.array_equiv(array_mixed_types, dm_array),
                            f"Input array {array_mixed_types} != from dm array {dm_array}")
            self.assertTrue(dm_dict == dict_mixed_types,
                            f"Input dict {dict_mixed_types} != from dm dict {dm_dict}")
            self.assertTrue(dataframe_mix_types.equals(dm_dataframe),
                            f"Input dataframe {dataframe_mix_types} != from dm dataframe {dm_dataframe}")

            # ----------------------------------
            # Check equality for dm_dict_as_dict_dataframe
            type_key_list = np.array(dict_as_dict_dataframe_types.keys())
            dm_key_list = np.array(dm_dict_as_dict_dataframe.keys())
            self.assertTrue((type_key_list == dm_key_list).all(),
                            f"key of dict_as_dict_dataframe {type_key_list} != from keys in dm {dm_key_list} ")
            # Check dataframes equality for dict_key_1
            type_dataframe_key_dict_key_1 = dict_as_dict_dataframe_types["dict_key_1"]
            dm_dataframe_key_dict_key_1 = dm_dict_as_dict_dataframe["dict_key_1"]
            self.assertTrue(type_dataframe_key_dict_key_1.equals(dm_dataframe_key_dict_key_1),
                            f"Dataframe of dict_as_dict_dataframe dict_key_1 {type_dataframe_key_dict_key_1} != from dm dataframe dict_key_1 {dm_dataframe_key_dict_key_1}")
            # Check dataframes equality for dict_key_3
            type_dataframe_key_dict_key_3 = dict_as_dict_dataframe_types["dict_key_3"]
            dm_dataframe_key_dict_key_3 = dm_dict_as_dict_dataframe["dict_key_3"]
            self.assertTrue(type_dataframe_key_dict_key_3.equals(dm_dataframe_key_dict_key_3),
                            f"Dataframe of dict_as_dict_dataframe dict_key_3 {type_dataframe_key_dict_key_3} != from dm dataframe dict_key_3 {dm_dataframe_key_dict_key_3}")

            array_file.close()
            dict_file.close()
            dataframe_file.close()
            dict_as_dict_dataframe_file.close()

    def test_delete_study_cases(self):
        from sos_trades_api.controllers.sostrades_main.study_case_controller import (
            delete_study_cases,
        )
        from sos_trades_api.models.database_models import StudyCase
        from sos_trades_api.tools.loading.study_case_manager import StudyCaseManager
        with DatabaseUnitTestConfiguration.app.app_context():
            study_test = StudyCase.query.filter(
                StudyCase.name == self.test_study_name).first()
            self.assertIsNotNone(study_test)
            studies_id_list_to_delete = [study_test.id]
        with DatabaseUnitTestConfiguration.app.app_context():
            delete_study_cases(studies_id_list_to_delete)

            study_test_deleted = StudyCase.query.filter(
                StudyCase.name == self.test_study_name).first()
            self.assertIsNone(
                study_test_deleted, "Error study case deleted has be found in database")
            # check that the folder of study data as been deleted
            self.assertFalse(os.path.exists(StudyCaseManager.get_root_study_data_folder(study_test.group_id,
                                                                                        study_test.id)),
                             "Error study case folder not deleted")

    def test_get_study_data_stream(self):
        from sos_trades_api.controllers.sostrades_main.study_case_controller import (
            get_study_data_stream,
        )
        from sos_trades_api.models.database_models import StudyCase
        with DatabaseUnitTestConfiguration.app.app_context():
            study_test = StudyCase.query.filter(
                StudyCase.name == self.test_study_name).first()
            self.assertIsNotNone(study_test)
            study_zip = get_study_data_stream(study_test.id)
            self.assertIsNotNone(study_zip)

    def _test_get_study_case_notifications(self):
        from sos_trades_api.controllers.sostrades_data.study_case_controller import (
            get_study_case_notifications,
        )
        from sos_trades_api.controllers.sostrades_main.study_case_controller import (
            update_study_parameters,
        )
        from sos_trades_api.models.database_models import StudyCase, User
        from sos_trades_api.models.loaded_study_case import LoadStatus
        from sos_trades_api.server.base_server import study_case_cache
        with DatabaseUnitTestConfiguration.app.app_context():
            study_test = StudyCase.query.filter(
                StudyCase.name == self.test_study_name).first()
            self.assertIsNotNone(study_test)

            user_test = User.query.filter(User.id == self.test_user_id).first()
            self.assertIsNotNone(user_test)

            initial_modification_date = study_test.modification_date
            parameters_update_list = [
                {"variableId": f"{study_test.name}.Disc1.a",
                 "variableType": "float",
                 "changeType": "scalar",
                 "newValue": 10,
                 "oldValue": 5,
                 "namespace": f"{study_test.name}",
                 "discipline": "Disc1",
                 "lastModified": "2021-01-11T13:51:26.118Z", "id": None, "author": None},
            ]

            study_manager = study_case_cache.get_study_case(study_test.id, False)
            columns_to_delete = []
            # updating study case
            update_study_parameters(
                study_test.id, user_test, None, None, parameters_update_list, columns_to_delete)

            #  wait until study was updated (thread behind)
            stop = False
            counter = 0

            while not stop:
                if study_manager.load_status == LoadStatus.LOADED:
                    stop = True
                else:
                    if counter > 60:
                        self.assertTrue(
                            False, "test_update_study_parameters update study parameter too long, check thread")
                    counter = counter + 1
                    sleep(1)

            # After update retrieve notification list, one update has been
            # made, return len should be 1
            notifications = get_study_case_notifications(study_test.id)
            change = notifications[0].changes[0]
            self.assertIsNotNone(
                change, "Error no change created at study update in database")
            self.assertEqual(change.variable_id, f"{study_test.name}.Disc1.a")
            self.assertEqual(change.change_type, "scalar")
            self.assertEqual(change.new_value, 10)
            self.assertEqual(change.old_value, 5)

    def test_get_user_authorised_studies_for_process(self):
        from sos_trades_api.controllers.sostrades_data.study_case_controller import (
            get_user_authorised_studies_for_process,
        )
        from sos_trades_api.models.database_models import StudyCase
        with DatabaseUnitTestConfiguration.app.app_context():
            study_test = StudyCase.query.filter(
                StudyCase.name == self.test_study_name).first()
            self.assertIsNotNone(
                study_test, "Unable to retrieve study case created and updated for test")
            user_authorised_studies = get_user_authorised_studies_for_process(self.test_user_id,
                                                                              self.test_process_name,
                                                                              self.test_repository_name)

            self.assertEqual(user_authorised_studies[0].process, self.test_process_name,
                             "Copied study case process does not match, test set up process name used")
            self.assertEqual(user_authorised_studies[0].repository, self.test_repository_name,
                             "Copied study case repository does not match, test set up repository name used")

    def test_get_user_study_case_preference(self):

        from sqlalchemy.sql.expression import and_

        from sos_trades_api.controllers.sostrades_data.study_case_controller import (
            load_study_case_preference,
            save_study_case_preference,
        )
        from sos_trades_api.models.database_models import UserStudyPreference

        # Load preference (will be empty)
        preference = load_study_case_preference(
            self.test_study_id, self.test_user_id)
        self.assertEqual(len(preference), 0,
                         "Initial preference data must be empty")

        # Set some preference data into the database
        first_panel_identifier = "key1"
        first_panel_opened = True
        second_panel_identifier = "key2"
        second_panel_opened = True

        save_study_case_preference(
            self.test_study_id, self.test_user_id, first_panel_identifier, first_panel_opened)
        save_study_case_preference(
            self.test_study_id, self.test_user_id, second_panel_identifier, second_panel_opened)

        with DatabaseUnitTestConfiguration.app.app_context():
            preference = UserStudyPreference.query.filter(
                and_(UserStudyPreference.user_id == self.test_user_id,
                     UserStudyPreference.study_case_id == self.test_study_id,
                     UserStudyPreference.panel_identifier == first_panel_identifier)).first()

            self.assertIsNotNone(preference, f"The identifier '{first_panel_identifier}', not found in database")

            preference_2 = UserStudyPreference.query.filter(
                and_(UserStudyPreference.user_id == self.test_user_id,
                     UserStudyPreference.study_case_id == self.test_study_id,
                     UserStudyPreference.panel_identifier == second_panel_identifier)).first()

            self.assertIsNotNone(preference_2, f"The identifier '{second_panel_identifier}', not found in database")

        # Load preference
        preference = load_study_case_preference(
            self.test_study_id, self.test_user_id)

        self.assertEqual(len(preference), 2,
                         "Preference data must be have two new entries")

    def _test_clear_error_in_study_case_controller(self):
        from os.path import dirname, join

        from numpy import array
        from werkzeug.datastructures import FileStorage

        from sos_trades_api.controllers.sostrades_main.study_case_controller import (
            update_study_parameters,
        )
        from sos_trades_api.models.database_models import StudyCase, User
        from sos_trades_api.models.loaded_study_case import LoadStatus
        from sos_trades_api.server.base_server import study_case_cache
        from sos_trades_api.tests import data

        with DatabaseUnitTestConfiguration.app.app_context():
            study_clear_error_test = StudyCase.query.filter(
                StudyCase.id == self.test_study_clear_error_id).first()
            self.assertIsNotNone(study_clear_error_test)

            study_manager = study_case_cache.get_study_case(study_clear_error_test.id, False)

            user_test = User.query.filter(User.id == self.test_user_id).first()
            self.assertIsNotNone(user_test)

            dataframe_path = join(dirname(data.__file__),
                                  "wrong_design_space.csv")
            dataframe_file = open(dataframe_path, "rb")
            dataframe_fs = FileStorage(dataframe_file)

            file_info = {
                dataframe_path: {"variable_id": f"{self.test_study_clear_error_name}.SellarOptimScenario.design_space",
                                 "discipline": "sostrades_core.execution_engine.sos_optim_scenario",
                                 "namespace": f"{self.test_study_clear_error_name}.SellarOptimScenario"},
            }
            files_list = [dataframe_fs]
            columns_to_delete = []
            # updating study case with wrong design space
            update_study_parameters(
                study_clear_error_test.id, user_test, files_list, file_info, [], columns_to_delete)

            #  wait until study was updated (thread behind)
            stop = False
            counter = 0

            while not stop:
                if study_manager.load_status == LoadStatus.IN_ERROR:
                    stop = True
                else:
                    if counter > 60:
                        self.assertTrue(
                            False, "test_csv_update_study_parameters update study parameter too long, check thread")
                    counter = counter + 1
                    sleep(1)

            self.assertTrue(study_manager.load_status == LoadStatus.IN_ERROR)

            error_message = "The current value of variable test_clear_error.SellarOptimScenario.z!15.0 is not between the lower bound 0.0 and the upper bound 10.0"
            self.assertIn(error_message, study_manager.error_message)

            dataframe_path = join(dirname(data.__file__),
                                  "correct_design_space.csv")
            dataframe_file = open(dataframe_path, "rb")
            dataframe_fs = FileStorage(dataframe_file)

            file_info = {
                dataframe_path: {"variable_id": f"{self.test_study_clear_error_name}.SellarOptimScenario.design_space",
                                 "discipline": "sostrades_core.execution_engine.sos_optim_scenario",
                                 "namespace": f"{self.test_study_clear_error_name}.SellarOptimScenario"},
            }
            files_list = [dataframe_fs]

            # other inputs to configure the process
            parameters_update_list = [
                {"variableId": f"{self.test_study_clear_error_name}.SellarOptimScenario.x",
                 "variableType": "array",
                 "changeType": "scalar",
                 "newValue": array([1.]),
                 "oldValue": None,
                 "namespace": f"{self.test_study_clear_error_name}.SellarOptimScenario",
                 "discipline": "sostrades_core.execution_engine.sos_optim_scenario",
                 "lastModified": "2021-01-11T13:51:26.118Z", "id": None, "author": None},

                {"variableId": f"{self.test_study_clear_error_name}.SellarOptimScenario.z",
                 "variableType": "array",
                 "changeType": "scalar",
                 "newValue": array([1., 1.]),
                 "oldValue": None,
                 "namespace": f"{self.test_study_clear_error_name}.SellarOptimScenario",
                 "discipline": "sostrades_core.execution_engine.sos_optim_scenario",
                 "lastModified": "2021-01-11T13:51:26.118Z", "id": None, "author": None},

                {"variableId": f"{self.test_study_clear_error_name}.SellarOptimScenario.Sellar_Problem.local_dv",
                 "variableType": "float",
                 "changeType": "scalar",
                 "newValue": 10.,
                 "oldValue": None,
                 "namespace": f"{self.test_study_clear_error_name}.SellarOptimScenario.Sellar_Problem",
                 "discipline": "sostrades_core.sos_wrapping.test_discs.sellar.SellarProblem",
                 "lastModified": "2021-01-11T13:51:26.118Z", "id": None, "author": None},

                {"variableId": f"{self.test_study_clear_error_name}.SellarOptimScenario.max_iter",
                 "variableType": "int",
                 "changeType": "scalar",
                 "newValue": 2,
                 "oldValue": None,
                 "namespace": f"{self.test_study_clear_error_name}.SellarOptimScenario",
                 "discipline": "sostrades_core.execution_engine.sos_optim_scenario",
                 "lastModified": "2021-01-11T13:51:26.118Z", "id": None, "author": None},

                {"variableId": f"{self.test_study_clear_error_name}.SellarOptimScenario.algo",
                 "variableType": "string",
                 "changeType": "scalar",
                 "newValue": "L-BFGS-B",
                 "oldValue": None,
                 "namespace": f"{self.test_study_clear_error_name}.SellarOptimScenario",
                 "discipline": "sostrades_core.execution_engine.sos_optim_scenario",
                 "lastModified": "2021-01-11T13:51:26.118Z", "id": None, "author": None},

                {"variableId": f"{self.test_study_clear_error_name}.SellarOptimScenario.formulation",
                 "variableType": "string",
                 "changeType": "scalar",
                 "newValue": "DisciplinaryOpt",
                 "oldValue": None,
                 "namespace": f"{self.test_study_clear_error_name}.SellarOptimScenario",
                 "discipline": "sostrades_core.execution_engine.sos_optim_scenario",
                 "lastModified": "2021-01-11T13:51:26.118Z", "id": None, "author": None},

                {"variableId": f"{self.test_study_clear_error_name}.SellarOptimScenario.objective_name",
                 "variableType": "string",
                 "changeType": "scalar",
                 "newValue": "obj",
                 "oldValue": None,
                 "namespace": f"{self.test_study_clear_error_name}.SellarOptimScenario",
                 "discipline": "sostrades_core.execution_engine.sos_optim_scenario",
                 "lastModified": "2021-01-11T13:51:26.118Z", "id": None, "author": None},

                {"variableId": f"{self.test_study_clear_error_name}.SellarOptimScenario.algo_options",
                 "variableType": "dict",
                 "changeType": "scalar",
                 "newValue": {"ftol_rel": 1e-6, "ineq_tolerance": 1e-6, "normalize_design_space": True},
                 "oldValue": None,
                 "namespace": f"{self.test_study_clear_error_name}.SellarOptimScenario",
                 "discipline": "sostrades_core.execution_engine.sos_optim_scenario",
                 "lastModified": "2021-01-11T13:51:26.118Z", "id": None, "author": None},

                {"variableId": f"{self.test_study_clear_error_name}.SellarOptimScenario.ineq_constraints",
                 "variableType": "array",
                 "changeType": "scalar",
                 "newValue": [],
                 "oldValue": None,
                 "namespace": f"{self.test_study_clear_error_name}.SellarOptimScenario",
                 "discipline": "sostrades_core.execution_engine.sos_optim_scenario",
                 "lastModified": "2021-01-11T13:51:26.118Z", "id": None, "author": None},
            ]
            columns_to_delete = []
            # updating study case with correct design space
            update_study_parameters(
                study_clear_error_test.id, user_test, files_list, file_info, parameters_update_list, columns_to_delete)

            #  wait until study was updated (thread behind)
            stop = False
            counter = 0

            while not stop:
                if study_manager.load_status == LoadStatus.LOADED:
                    stop = True
                else:
                    if counter > 60:
                        self.assertTrue(
                            False, "test_csv_update_study_parameters update study parameter too long, check thread")
                    counter = counter + 1
                    sleep(1)

            # check if clear_error is performed in study_case_controller
            self.assertFalse(study_manager.load_status == LoadStatus.IN_ERROR)

    def test_study_case_read_only_mode(self):
        from sos_trades_api.controllers.sostrades_data.study_case_controller import (
            create_empty_study_case,
        )
        from sos_trades_api.controllers.sostrades_main.study_case_controller import (
            delete_study_cases,
            load_or_create_study_case,
        )
        from sos_trades_api.models.database_models import AccessRights, StudyCase
        from sos_trades_api.models.loaded_study_case import LoadStatus
        from sos_trades_api.server.base_server import study_case_cache
        from sos_trades_api.tools.study_management.study_management import get_read_only

        with DatabaseUnitTestConfiguration.app.app_context():
            study_test = StudyCase.query.filter(
                StudyCase.name == self.test_study_csv_name).first()
            self.assertIsNotNone(
                study_test, "Unable to retrieve study case created for test")
            study_copy_name = "test_study_copy_read_only"

            new_study_case = create_empty_study_case(self.test_user_id,
                                                     study_copy_name,
                                                     study_test.repository,
                                                     study_test.process,
                                                     self.test_user_group_id,
                                                     str(study_test.id),
                                                     StudyCase.FROM_STUDYCASE,
                                                     None,
                                                     None,
                                                     )

            load_or_create_study_case(new_study_case.id)
            study_case_copy_id = new_study_case.id
            # wait end of study case creation
            study_manager = study_case_cache.get_study_case(study_case_copy_id, False)
            #  wait until study was updated (thread behind)
            stop = False
            counter = 0

            while not stop:
                if study_manager.load_status == LoadStatus.LOADED:
                    stop = True
                else:
                    if counter > 60:
                        self.assertTrue(
                            False, "test_update_study_parameters update study parameter too long, check thread")
                    counter = counter + 1
                    sleep(1)
            self.assertTrue(study_manager.check_study_case_json_file_exists(
            ), "Unable to retrieve study case read only file")
            study_json = get_read_only(study_case_copy_id, AccessRights.MANAGER)
            self.assertIsNotNone(
                study_json, "Unable to read study case read only file")

            # check that the json contains the data
            self.assertTrue(
                "test_study_copy_read_only.dataframe_mix_types" in str(study_json),
                "the parameter is not in the read only file")

            studies_id_list_to_delete = [study_case_copy_id]
            delete_study_cases(studies_id_list_to_delete)

    def test_study_case_update_parameter_from_dataset_mapping_import(self):
        from sos_trades_api.controllers.sostrades_data.study_case_controller import (
            create_empty_study_case,
            create_new_notification_after_update_parameter,
            get_last_study_case_changes,
        )
        from sos_trades_api.controllers.sostrades_main.study_case_controller import (
            delete_study_cases,
            load_or_create_study_case,
            update_study_parameters_from_datasets_mapping,
        )
        from sos_trades_api.models.database_models import (
            StudyCase,
            StudyCaseChange,
            User,
        )
        from sos_trades_api.models.loaded_study_case import LoadStatus
        from sos_trades_api.server.base_server import study_case_cache
        from sos_trades_api.tools.coedition.coedition import UserCoeditionAction

        with DatabaseUnitTestConfiguration.app.app_context():
            user_test = User.query.filter(User.username == User.STANDARD_USER_ACCOUNT_NAME).first()
            self.assertIsNotNone(user_test)
            study_test = StudyCase.query.filter(
                StudyCase.name == self.test_study_csv_name).first()
            self.assertIsNotNone(
                study_test, "Unable to retrieve study case created for test")
            study_copy_name = "test_study_for_dataset_mapping"

            new_study_case = create_empty_study_case(self.test_user_id,
                                                     study_copy_name,
                                                     study_test.repository,
                                                     study_test.process,
                                                     self.test_user_group_id,
                                                     str(study_test.id),
                                                     StudyCase.FROM_STUDYCASE,
                                                     None,
                                                     None,
                                                     )

            load_or_create_study_case(new_study_case.id)
            study_case_copy_id = new_study_case.id
            # wait end of study case creation
            study_manager = study_case_cache.get_study_case(study_case_copy_id, False)
            #  wait until study was updated (thread behind)
            stop = False
            counter = 0

            while not stop:
                if study_manager.load_status == LoadStatus.LOADED:
                    stop = True
                else:
                    if counter > 60:
                        self.assertTrue(
                            False, "test_study_for_dataset_mapping update study parameter from dataset mapping too long, check thread")
                    counter = counter + 1
                    sleep(1)

            files_data = {
                "process_module_path": "sostrades_core.sos_processes.test.test_disc1_disc2_dataset",
                "namespace_datasets_mapping": {
                    "v0|<study_ph>.test_disc1_disc2_coupling.Disc1|*":
                        ["MVP0_datasets_connector|default_numerical_parameters|*",
                         "MVP0_datasets_connector|dataset_a|*"],
                },
            }
            user_test = User.query.filter(User.username == User.STANDARD_USER_ACCOUNT_NAME).first()
            # Create new notification
            notification_id = create_new_notification_after_update_parameter(study_case_copy_id, StudyCaseChange.DATASET_MAPPING_CHANGE, UserCoeditionAction.SAVE, user_test)

            user_test = User.query.filter(User.username == User.STANDARD_USER_ACCOUNT_NAME).first()
            # Update data from dataset_mapping with an error on the namespace_datasets_mapping
            update_study_parameters_from_datasets_mapping(study_case_copy_id, user_test, files_data, notification_id)

            #  wait until study was updated (thread behind)
            stop = False
            counter = 0

            while not stop:
                if study_manager.load_status == LoadStatus.LOADED:
                    stop = True
                else:
                    if counter > 60:
                        self.assertTrue(
                            False, "test_study_for_dataset_mapping update study parameter from dataset mapping too long, check thread")
                    counter = counter + 1
                    sleep(1)

            # check if clear_error is performed in study_case_controller
            self.assertFalse(study_manager.load_status == LoadStatus.IN_ERROR)
            parameter_changes = get_last_study_case_changes(new_study_case.id)
            self.assertTrue(len(parameter_changes) == 0)

            files_data = {
                "process_module_path": "sostrades_core.sos_processes.test.test_disc1_disc2_dataset",
                "namespace_datasets_mapping": {
                    "v0|<study_ph>.Disc1|*":
                        ["MVP0_datasets_connector|dataset_a|*"],
                },
            }
            user_test = User.query.filter(User.username == User.STANDARD_USER_ACCOUNT_NAME).first()
            # Create new notification
            notification_id = create_new_notification_after_update_parameter(study_case_copy_id, StudyCaseChange.DATASET_MAPPING_CHANGE, UserCoeditionAction.SAVE, user_test)
            # Update data from dataset_mapping without an error on the namespace_datasets_mapping
            user_test = User.query.filter(User.username == User.STANDARD_USER_ACCOUNT_NAME).first()
            update_study_parameters_from_datasets_mapping(study_case_copy_id, user_test, files_data, notification_id)

            #  wait until study was updated (thread behind)
            stop = False
            counter = 0

            while not stop:
                if study_manager.load_status == LoadStatus.LOADED:
                    stop = True
                else:
                    if counter > 60:
                        self.assertTrue(
                            False, "test_study_for_dataset_mapping update study parameter from dataset mapping too long, check thread")
                    counter = counter + 1
                    sleep(1)

            # check if clear_error is performed in study_case_controller
            self.assertFalse(study_manager.load_status == LoadStatus.IN_ERROR)
            parameter_changes = get_last_study_case_changes(new_study_case.id)
            for parameter in parameter_changes:
                if parameter.variable_id == "test_study_for_dataset_mapping.test_disc1_disc2_coupling.Disc1.a":
                    self.assertIsNotNone(parameter.datase_id)
                    self.assertIsNotNone(parameter.datase_connector_id)
                    self.assertEqual(parameter.old_value, 5)
                    self.assertEqual(parameter.new_value, 15)

            studies_id_list_to_delete = [study_case_copy_id]
            delete_study_cases(studies_id_list_to_delete)
