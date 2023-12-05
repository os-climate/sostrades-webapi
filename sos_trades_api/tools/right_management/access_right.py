"""
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
"""
"""
mode: python; py-indent-offset: 4; tab-width: 4; coding: utf-8
tools methods to check user access right on API resources
"""

from sos_trades_api.models.database_models import UserProfile
from typing import List

APP_MODULE_STUDY = 'STUDY'
APP_MODULE_EXECUTION = 'EXECUTION'
APP_MODULE_STUDY_MANAGER = 'STUDY_MANAGER'


def get_applicative_module(user_profile_id: int) -> List[str]:
    """Method that check applicative module access regarding profile id

    Return the profile application module list

    :param user_profile_id: profile identifier to check
    :type user_profile_id: int
    """

    profile = UserProfile.query.filter(
        UserProfile.id == user_profile_id).first()

    result = []

    if profile is not None:
        if profile.name == UserProfile.STUDY_MANAGER:
            result = [APP_MODULE_STUDY, APP_MODULE_STUDY_MANAGER, APP_MODULE_EXECUTION]
        elif profile.name == UserProfile.STUDY_USER:
            result = [APP_MODULE_STUDY, APP_MODULE_EXECUTION]
        elif profile.name == UserProfile.STUDY_USER_NO_EXECUTION:
            result = [APP_MODULE_STUDY]

    return result


def has_access_to(user_profile_id, applicative_module) -> bool:
    """ Method that check applicative module access regarding profile id

    :param user_profile_id: profile identifier to check
    :type user_profile_id: int

    :param applicative_module: applicative to check regarding the user profile
    :type applicative_module: str
    """

    profile = UserProfile.query.filter(
        UserProfile.id == user_profile_id).first()

    result = False

    if profile is not None:
        if profile.name == UserProfile.STUDY_MANAGER:
            result = applicative_module == APP_MODULE_STUDY_MANAGER or applicative_module == APP_MODULE_STUDY or applicative_module == APP_MODULE_EXECUTION
        elif profile.name == UserProfile.STUDY_USER :
            result = applicative_module == APP_MODULE_STUDY or applicative_module == APP_MODULE_EXECUTION
        elif profile.name == UserProfile.STUDY_USER_NO_EXECUTION:
            result = applicative_module == APP_MODULE_STUDY

    return result


def check_user_is_manager(user_profile_id):
    """ Method that check if user is manager regarding his profile id

       :param user_profile_id: profile identifier to check
       :type user_profile_id: int

       :return boolean
       """

    result = False
    profile = UserProfile.query.filter(UserProfile.id == user_profile_id).first()
    if profile is not None:
        if profile.name == UserProfile.STUDY_MANAGER:
            result = True
    return result
