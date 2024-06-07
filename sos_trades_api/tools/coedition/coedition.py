'''
Copyright 2022 Airbus SAS
Modifications on 2023/08/30-2023/11/03 Copyright 2023 Capgemini

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
from sos_trades_api.models.user_dto import UserDto

"""
mode: python; py-indent-offset: 4; tab-width: 4; coding: utf-8
tools methods to manage coedition features
"""

from datetime import datetime

from sos_trades_api.models.database_models import (
    Notification,
    StudyCase,
    StudyCaseChange,
    StudyCoeditionUser,
    User,
)
from sos_trades_api.server.base_server import db


class UserCoeditionAction:
    JOIN_ROOM = 'connection'
    LEAVE_ROOM = 'disconnection'
    SAVE = 'save'
    SUBMISSION = 'submission'
    EXECUTION = 'execution'
    CLAIM = 'claim'
    RELOAD = 'reload'
    EDIT = 'edit'
    DELETE = 'delete'
    VALIDATION_CHANGE = 'validation_change'

    @classmethod
    def get_attribute_for_value(cls, value):
        """Get the attribute name for the given value in the UserCoeditionAction class."""
        for attr_name, attr_value in cls.__dict__.items():
            if attr_value == value:
                return attr_name
        return None


class CoeditionMessage:
    JOIN_ROOM = 'User has entered the study case.'
    LEAVE_ROOM = 'User just left the study case.'
    SAVE = 'User just saved the study case.'
    SUBMISSION = 'User just submitted to execution the study case.'
    EXECUTION = 'Study case execution just started.'
    CLAIM = 'User just claimed the study case execution right.'
    RELOAD = 'User just reload the study case.'
    IMPORT_DATASET = 'User just updated parameter from dataset'


def add_user_to_room(user_id, study_case_id):
    """ Add user to a room (room id = study_case_id)
    """

    # Check if user is already in room
    user_study_exist = StudyCoeditionUser.query.filter(
        StudyCoeditionUser.user_id == user_id).filter(
            StudyCoeditionUser.study_case_id == study_case_id).first()

    if user_study_exist is None:
        new_user_room = StudyCoeditionUser()
        new_user_room.user_id = user_id
        new_user_room.study_case_id = study_case_id

        db.session.add(new_user_room)
        db.session.commit()


def remove_user_from_room(user_id, study_case_id):
    """ Remove user from a room (room id = study_id)
    """

    user_removed_room = StudyCoeditionUser.query.filter(
        StudyCoeditionUser.user_id == user_id).filter(
            StudyCoeditionUser.study_case_id == study_case_id).first()

    if user_removed_room is not None:
        db.session.delete(user_removed_room)
        db.session.commit()


def remove_user_from_all_rooms(user_id):
    """ Remove user from all rooms
    """

    user_to_delete = StudyCoeditionUser.query.filter(
        StudyCoeditionUser.user_id == user_id).all()

    if len(user_to_delete) > 0:
        for utd in user_to_delete:
            db.session.delete(utd)
        db.session.commit()


def get_user_list_in_room(study_case_id):
    """ Get user list present in a room (room id = study_case_id)
    """
    user_dto_list = []
    users_in_room = User.query.join(StudyCoeditionUser).join(StudyCase).filter(
        StudyCoeditionUser.study_case_id == study_case_id).filter(StudyCoeditionUser.user_id == User.id).all()
    for user in users_in_room:
        user_dto = UserDto(user.id)
        user_dto.username = user.username
        user_dto.lastname = user.lastname
        user_dto.firstname = user.firstname
        user_dto_list.append(user_dto)

    result = [ur.serialize() for ur in user_dto_list]

    return result

def add_notification_db(study_case_id, user, coedition_type: UserCoeditionAction, message):
    """ Add coedition study notification to database
    """
    # Check if coedition_type is a UserCoeditionAction and if user is an instance of the User class
    if coedition_type not in vars(UserCoeditionAction).values():
        raise ValueError("coedition_type must be a coedition action.")
    if not isinstance(user, User):
        raise ValueError("user must be an instance of the User class.")

    new_notification = Notification()
    new_notification.author = f'{user.firstname} {user.lastname}'
    new_notification.study_case_id = study_case_id
    new_notification.created = datetime.now()
    new_notification.type = coedition_type
    new_notification.message = message

    # Save notification
    db.session.add(new_notification)
    db.session.commit()

    return new_notification.id


def add_change_db(notification_id, variable_id, variable_type, deleted_columns, change_type, new_value,
                  old_value, old_value_blob, last_modified, dataset_connector_id, dataset_id, dataset_parameter_id):
    """ Add study change to database
    """
    new_change = StudyCaseChange()

    new_change.notification_id = notification_id
    new_change.variable_id = variable_id
    new_change.variable_type = variable_type
    new_change.change_type = change_type
    new_change.new_value = new_value
    new_change.old_value = old_value
    new_change.old_value_blob = old_value_blob
    new_change.last_modified = last_modified
    new_change.deleted_columns = deleted_columns
    new_change.dataset_connector_id = dataset_connector_id
    new_change.dataset_id = dataset_id
    new_change.dataset_parameter_id = dataset_parameter_id

    # Save change
    db.session.add(new_change)
    db.session.commit()
