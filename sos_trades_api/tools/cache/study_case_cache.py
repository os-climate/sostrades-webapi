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
import threading
from sos_trades_api.tools.loading.loading_study_and_engine import study_need_to_be_updated
from sos_trades_api.tools.loading.study_case_manager import StudyCaseManager


class StudyCaseReference:
    def __init__(self, study_id, modification_date):
        self.study_id = study_id
        self.modification_date = modification_date


class StudyCaseCache:

    def __init__(self):
        self.__study_case_dict = {}
        self.__exec_engine_dict = {}
        self.__lock_cache = {}

    def is_study_case_cached(self, study_case_id):
        return study_case_id in self.__study_case_dict

    def delete_study_case_from_cache(self, study_case_id):
        if self.is_study_case_cached(study_case_id):
            del self.__study_case_dict[study_case_id]
            del self.__exec_engine_dict[study_case_id]
            del self.__lock_cache[study_case_id]

    def add_study_case_in_cache_from_values(self, studycase, exec_engine):

        if not self.is_study_case_cached(studycase.id):
            self.__study_case_dict[studycase.id] = StudyCaseReference(
                studycase.id, studycase.modification_date)
            self.__exec_engine_dict[studycase.id] = exec_engine
            self.__lock_cache[studycase.id] = threading.Lock()
        else:
            try:
                self.__lock_cache[studycase.id].acquire()
                self.__study_case_dict[studycase.id] = StudyCaseReference(
                    studycase.id, studycase.modification_date)
                self.__exec_engine_dict[studycase.id] = exec_engine
                self.__lock_cache[studycase.id] = threading.Lock()
            except Exception as error:
                print(error)
            finally:
                self.release_study_case(studycase.id)

    def __add_study_case_in_cache_from_database(self, study_case_id):
        """ Request a study loading and add it into the server cache

        :params: study_case_identifier, database key og the study to load
        :type: int
        """

        if not self.is_study_case_cached(study_case_id):
            study_case_manager = StudyCaseManager(study_case_id)
        else:
            study_case_manager = self.__exec_engine_dict[study_case_id]
            old_modification_date = study_case_manager.study.modification_date
            study_case_manager.update_study_case()

            if old_modification_date < study_case_manager.study.modification_date:
                study_case_manager.loaded = False

        self.__study_case_dict[study_case_manager.study.id] = StudyCaseReference(
            study_case_manager.study.id,
            study_case_manager.study.modification_date)
        self.__exec_engine_dict[study_case_manager.study.id] = study_case_manager
        self.__lock_cache[study_case_manager.study.id] = threading.Lock()

    def get_study_case(self, study_case_id, with_lock, check_expire=True):

        if not self.is_study_case_cached(study_case_id):
            self.__add_study_case_in_cache_from_database(study_case_id)
        elif check_expire:
            if study_need_to_be_updated(
                    study_case_id, self.__study_case_dict[study_case_id].modification_date):
                try:
                    self.__lock_cache[study_case_id].acquire()
                    self.__add_study_case_in_cache_from_database(
                        study_case_id)
                except Exception as error:
                    print(error)
                finally:
                    self.release_study_case(study_case_id)

        if with_lock:
            self.__lock_cache[study_case_id].acquire()

        return self.__exec_engine_dict[study_case_id]

    def release_study_case(self, study_case_id):

        if self.is_study_case_cached(study_case_id):

            if self.__lock_cache[study_case_id].locked():
                self.__lock_cache[study_case_id].release()

    def update_study_case_modification_date(self, study_case_id, modification_date):
        if self.is_study_case_cached(study_case_id):
            self.__study_case_dict[study_case_id].modification_date = modification_date
            self.release_study_case(study_case_id)
