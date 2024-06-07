'''
Copyright 2022 Airbus SAS
Modifications on 2023/11/17-2023/11/23 Copyright 2023 Capgemini

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
import logging
import threading
from datetime import datetime, timedelta

from sos_trades_api.tools.loading.loading_study_and_engine import (
    study_need_to_be_updated,
)
from sos_trades_api.tools.loading.study_case_manager import StudyCaseManager


class StudyCaseReference:
    """
    Class that store last modification date regarding a study case in order to manage study case update
    """

    def __init__(self, study_identifier, modification_date):
        """
        Constructor

        :param study_identifier: study case identifier
        :type study_identifier: int
        :param modification_date: modification date to store
        :type modification_date: datetime
        """
        self.__study_identifier = study_identifier
        self.__modification_date = modification_date

    @property
    def study_identifier(self):
        """
        Getter on study identifier

        :return: int
        """
        return self.__study_identifier

    @property
    def modification_date(self):
        """
        Getter on modification date

        :return: datetime
        """
        return self.__modification_date

    @modification_date.setter
    def modification_date(self, value):
        """
        Setter on modification date

        :param value: new date to set
        :type value: datetime
        """

        if not self.__modification_date == value:
            self.__modification_date = value


class StudyCaseCache:
    """
    Class that manage to store in memory several StudyCaseManager instances
    """

    # elapsed time between two saving of the last active date of a study in seconds
    ACTIVE_DATE_ELAPSED_WRITTING_TIME = 5

    def __init__(self, logger=logging.getLogger(__name__)):
        """
        Constructor
        """
        self.__study_case_dict = {}
        self.__study_case_manager_dict = {}
        self.__lock_cache = {}
        self.__last_alive_date = {}

    def is_study_case_cached(self, study_case_identifier):
        """
        Determine if study case identifier given in parameter is already tored in cache

        :param study_case_identifier: study case identifier to check
        :type study_case_identifier: int
        :return: boolean
        """
        return study_case_identifier in self.__study_case_dict

    def delete_study_case_from_cache(self, study_case_identifier):
        """
        Remove a StudyCaseManager instance from cache using study case identifier

        :param study_case_identifier: study case identifier to remove
        :type study_case_identifier: int
        """
        if self.is_study_case_cached(study_case_identifier):
            # Detach logger
            self.__study_case_manager_dict[study_case_identifier].detach_logger()
            del self.__study_case_dict[study_case_identifier]
            del self.__study_case_manager_dict[study_case_identifier]
            del self.__lock_cache[study_case_identifier]

    def add_study_case_in_cache_from_values(self, study_case_manager):
        """
        Manually add and already existing instance of a StudyCaseManager into the cache

        :param study_case_manager: StudyCaseManager instance to add
        :type study_case_manager: sos_trades_api.tools.loading.study_case_manager.StudyCaseManager
        """

        study_case_manager.attach_logger()
        study_case = study_case_manager.study
        if not self.is_study_case_cached(study_case.id):
            self.__study_case_dict[study_case.id] = StudyCaseReference(
                study_case.id, study_case.modification_date
            )
            self.__study_case_manager_dict[study_case.id] = study_case_manager
            self.__lock_cache[study_case.id] = threading.Lock()
        else:
            try:
                self.__lock_cache[study_case.id].acquire()
                self.__study_case_dict[study_case.id] = StudyCaseReference(
                    study_case.id, study_case.modification_date
                )
                self.__study_case_manager_dict[study_case.id].detach_logger()
                self.__study_case_manager_dict[study_case.id] = study_case_manager
                self.__lock_cache[study_case.id] = threading.Lock()
            except Exception as error:
                self.logger.error("Error while add_study_case_in_cache_from_values", exc_info=error)
            finally:
                self.release_study_case(study_case.id)

    def __add_study_case_in_cache_from_database(self, study_case_identifier):
        """
        Add a new study cae into the cache

        :param study_case_identifier: identifier of the study to add to tha cache
        :type study_case_identifier: int
        """

        study_case_manager = StudyCaseManager(study_case_identifier)
        study_case_manager.attach_logger()

        self.__study_case_dict[study_case_manager.study.id] = StudyCaseReference(
            study_case_manager.study.id, study_case_manager.study.modification_date
        )
        
        self.__study_case_manager_dict[study_case_manager.study.id] = study_case_manager
        self.__lock_cache[study_case_manager.study.id] = threading.Lock()

    def get_study_case(self, study_case_identifier, with_lock, check_expire=True):
        """
        Retrieve a study case from the cache with option to update it if expired

        :param study_case_identifier: study case identifier to retrieve
        :type study_case_identifier: int
        :param with_lock: lock or not inner dictionary  regarding thread safe action
        :type with_lock: boolean
        :param check_expire: check or not if the study case has to be refresh
        :type check_expire: boolean
        :return: sos_trades_api.tools.loading.study_case_manager.StudyCaseManager
        """

        if not self.is_study_case_cached(study_case_identifier):
            self.__add_study_case_in_cache_from_database(study_case_identifier)
        elif check_expire:
            if study_need_to_be_updated(
                study_case_identifier,
                self.__study_case_dict[study_case_identifier].modification_date,
            ):
                try:
                    self.__lock_cache[study_case_identifier].acquire()

                    self.__study_case_manager_dict[study_case_identifier].detach_logger()
                    self.__add_study_case_in_cache_from_database(study_case_identifier)
                except Exception as error:
                    self.logger.error("Error reloading study", exc_info=error)
                finally:
                    self.release_study_case(study_case_identifier)

        if with_lock:
            self.__lock_cache[study_case_identifier].acquire()

        return self.__study_case_manager_dict[study_case_identifier]

    def release_study_case(self, study_case_identifier):
        """
        Release study case lock if already locked

        :param study_case_identifier: study case identifier to unlock
        :type study_case_identifier: int
        """

        if self.is_study_case_cached(study_case_identifier):

            if self.__lock_cache[study_case_identifier].locked():
                self.__lock_cache[study_case_identifier].release()

    def update_study_case_modification_date(self, study_identifier, modification_date):
        """
        Update last modification date into the study case database object

        :param study_identifier: study case identifier
        :type study_identifier: int
        :param modification_date: modification date to store
        :type modification_date: datetime
        """
        if self.is_study_case_cached(study_identifier):
            self.__study_case_dict[study_identifier].modification_date = modification_date
            self.release_study_case(study_identifier)

    def update_study_case_last_active_date(self, study_case_id)->bool:
        '''
        update study case last active date in dict only if there is more than an elapsed time between 2 update

        '''
        has_been_updated = False
        delta_time = datetime.now() - timedelta(seconds=self.ACTIVE_DATE_ELAPSED_WRITTING_TIME)
        #update the last active date if it is more than 5s elapsed time
        if (study_case_id not in self.__last_alive_date 
            or self.__last_alive_date[study_case_id] < delta_time):
            self.__last_alive_date[study_case_id] = datetime.now()
            has_been_updated = True
        return has_been_updated

    def get_saved_active_study(self):
        return self.__last_alive_date.keys()