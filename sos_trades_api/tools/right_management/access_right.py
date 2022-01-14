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
tools methods to check user access right on API ressources
"""

from werkzeug.exceptions import Unauthorized
from sos_trades_api.models.database_models import StudyCase, StudyCaseAccessGroup,\
    UserProfile, Group, User, GroupAccessUser


APP_MODULE_ADMIN = 'ADMIN'
APP_MODULE_STUDY = 'STUDY'


def get_applicative_module(user_profile_id):
    """ Method that check applicative module access regarding profile id

    :params: user_profile_id, profile identifier to check
    :type: integer 

    :return: string[], applicative module list
    """

    profile = UserProfile.query.filter(
        UserProfile.id == user_profile_id).first()

    result = []

    if profile is not None:
        if profile.name == UserProfile.ADMIN_PROFILE:
            result = [APP_MODULE_ADMIN]
        if profile.name == UserProfile.STUDY_MANAGER:
            result = [APP_MODULE_STUDY]
        elif profile.name == UserProfile.STUDY_USER:
            result = [APP_MODULE_STUDY]

    return result


def has_access_to(user_profile_id, applicative_module):
    """ Method that check applicative module access regarding profile id

    :params: user_profile_id, profile identifier to check
    :type: integer

    :params: applicative_module, applicative to check regarding the user profile
    :type: string 

    :return: boolean
    """

    profile = UserProfile.query.filter(
        UserProfile.id == user_profile_id).first()

    result = False

    if profile is not None:
        if profile.name == UserProfile.ADMIN_PROFILE:
            result = applicative_module == APP_MODULE_ADMIN
        if profile.name == UserProfile.STUDY_MANAGER:
            result = applicative_module == APP_MODULE_ADMIN or applicative_module == APP_MODULE_STUDY
        elif profile.name == UserProfile.STUDY_USER:
            result = applicative_module == APP_MODULE_STUDY

    return result


def check_user_is_admin(user_id):
    """ Methods that check that the given user identifier is declared as
    administrator in the application

    :params: user_id
    :type: int

    :raise: Unauthorized exception if test failed
    """

    if not is_user_admin(user_id):
        raise Unauthorized(
            'You are not allowed to access this ressource')


def is_user_admin(user_id):
    """ Methods that check that the given user identifier is declared as
    administrator in the application

    :params: user_id
    :type: int

    :return boolean
    """
    user_admin = User.query.join(UserProfile).filter(
        UserProfile.name == UserProfile.ADMIN_PROFILE).filter(User.id == user_id).all()

    if user_admin == []:
        return False
    else:
        return True
