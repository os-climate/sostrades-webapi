'''
Copyright 2022 Airbus SAS
Modifications on 2023/08/30-2023/12/04 Copyright 2023 Capgemini

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
Database models
"""
from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime, UniqueConstraint, LargeBinary
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql.types import TEXT, LONGBLOB
from sos_trades_api.server.base_server import db
from datetime import datetime
import pytz
import uuid


class UserProfile(db.Model):
    STUDY_USER = 'Study user'
    STUDY_MANAGER = 'Study manager'
    STUDY_USER_NO_EXECUTION = 'Study user without execution'

    """UserProfile class"""

    id = Column(Integer, primary_key=True)
    name = Column(String(64), index=False, unique=True)
    description = Column(String(128), index=False, unique=False)

    def __repr__(self):
        """ Overload of the class representation
        """
        return f'{self.id} | {self.name} | {self.description}'

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }


class User(UserMixin, db.Model):
    STANDARD_USER_ACCOUNT_NAME = 'user_test'
    STANDARD_USER_ACCOUNT_EMAIL = f'{STANDARD_USER_ACCOUNT_NAME}@sostrades.com'

    LOCAL_ACCOUNT = 'local_account'
    IDP_ACCOUNT = 'idp_account'

    """User class"""

    id = Column(Integer, primary_key=True)
    username = Column(String(64), index=True, unique=True)
    firstname = Column(String(64), index=True, unique=False)
    lastname = Column(String(64), index=True, unique=False)
    email = Column(String(120), index=True, unique=True)
    department = Column(String(120), index=True, unique=False)
    company = Column(String(120), index=True, unique=False)
    password_hash = Column(String(128))
    is_logged = Column(Boolean, default=False)
    user_profile_id = Column(Integer,
                             ForeignKey(f'{UserProfile.__tablename__}.id',
                                        name='fk_user_user_profile_id'),
                             nullable=True)
    default_group_id = Column(Integer, nullable=True)
    reset_uuid = Column(String(length=36), nullable=True)
    account_source = Column(String(length=64), nullable=False, server_default=LOCAL_ACCOUNT)
    last_login_date = Column(DateTime(timezone=True), server_default=str(datetime.now().astimezone(pytz.UTC)))
    last_password_reset_date = Column(DateTime(timezone=True), server_default=str(datetime.now().astimezone(pytz.UTC)))

    def init_from_user(self, user):
        """
        Iniitialize current user instance using another without
        :param user: user to copy data
        """

        if user is not None:
            self.id = user.id
            self.username = user.username
            self.firstname = user.firstname
            self.lastname = user.lastname
            self.email = user.email
            self.department = user.department
            self.company = user.company
            self.password_hash = user.password_hash
            self.is_logged = user.is_logged
            self.default_group_id = user.default_group_id
            self.user_profile_id = user.user_profile_id
            self.reset_uuid = user.reset_uuid
            self.account_source = user.account_source
            self.last_login_date = user.last_login_date
            self.last_password_reset_date = user.last_password_reset_date

    def __repr__(self):
        """ Overload of the class representation

            Allow to hide password_hash from serializer point of view
        """
        return f'{self.id} | {self.username} | {self.email}'

    def set_password(self, password):
        """ Set the password and encode it
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """ Check the encoded password with the one given as parameter
        """
        return check_password_hash(self.password_hash, password)

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'id': self.id,
            'username': self.username,
            'firstname': self.firstname,
            'lastname': self.lastname,
            'userprofile': self.user_profile_id,
            'email': self.email,
            'department': self.department,
            'default_group_id': self.default_group_id,
            'internal_account': self.account_source == User.LOCAL_ACCOUNT
        }


class Group(db.Model):
    ALL_USERS_GROUP = 'All users'
    ALL_USERS_GROUP_DESCRIPTION = 'Default group for all SoSTrades users'

    SOS_TRADES_DEV_GROUP = 'SoSTrades_Dev'
    SOS_TRADES_DEV_GROUP_DESCRIPTION = 'SoSTrades development team group'

    """Group class"""
    id = Column(Integer, primary_key=True)
    name = Column(String(64), index=True, unique=True)
    creator_id = Column(Integer,
                        ForeignKey(
                            f'{User.__tablename__}.id',
                            name='fk_group_creator_id'),
                        nullable=True)
    creation_date = Column(DateTime(timezone=True), server_default=func.now())
    description = Column(String(255))
    confidential = Column(Boolean, default=False)
    is_default_applicative_group = Column(Boolean, default=False)

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'id': self.id,
            'name': self.name,
            'creator_id': self.creator_id,
            'creation_date': self.creation_date,
            'description': self.description,
            'confidential': self.confidential,
            'is_default_applicative_group': self.is_default_applicative_group,
        }


class Process(db.Model):
    """Process class"""

    id = Column(Integer, primary_key=True)
    name = Column(String(64), index=True)
    process_path = Column(String(255))
    disabled = Column(Boolean, default=False, nullable=False)

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'id': self.id,
            'name': self.name,
            'process_path': self.process_path
        }


class StudyCase(db.Model):
    """StudyCase class"""
    CREATION_NOT_STARTED = 'PENDING'
    CREATION_IN_PROGRESS = 'IN_PROGRESS'
    CREATION_DONE = 'DONE'
    CREATION_ERROR = 'IN_ERROR'

    FROM_REFERENCE = 'Reference'
    FROM_USECASE = 'UsecaseData'
    FROM_STUDYCASE = 'Study'

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer,
                      ForeignKey(f'{Group.__tablename__}.id',
                                 ondelete="CASCADE",
                                 name='fk_study_case_group_id'),
                      nullable=False)
    name = Column(String(64), index=True, unique=False)
    repository = Column(String(64), index=True, unique=False, server_default='test')
    process = Column(String(64), index=True, unique=False)
    process_id = Column(Integer,
                        ForeignKey(
                            f'{Process.__tablename__}.id',
                            name='fk_study_case_process_id'),
                        nullable=True)
    description = Column(TEXT, index=False, unique=False)
    creation_date = Column(DateTime(timezone=True), server_default=func.now())
    creation_status = Column(String(64), index=False, unique=False, server_default=CREATION_NOT_STARTED)
    reference = Column(String(64), unique=False, nullable=True)
    from_type = Column(String(64), unique=False)
    modification_date = Column(DateTime(timezone=True), server_default=func.now())
    user_id_execution_authorised = Column(Integer,
                                          ForeignKey(
                                              f'{User.__tablename__}.id',
                                              name='fk_study_case_user_id_execution_authorised'),
                                          nullable=True)
    current_execution_id = Column(Integer, nullable=True)
    error = Column(Text, index=False, unique=False, nullable=True)
    disabled = Column(Boolean, default=False, nullable=False)

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'id': self.id,
            'name': self.name,
            'repository': self.repository,
            'process': self.process,
            'description': self.description,
            'creation_date': self.creation_date,
            'modification_date': self.modification_date,
            'reference': self.reference,
            'from_type': self.from_type,
            'creation_status': self.creation_status,
        }


class StudyCaseAllocation(db.Model):
    """StudyCaseAllocation class"""

    NOT_STARTED = 'NOT_STARTED'
    IN_PROGRESS = 'IN_PROGRESS'
    PENDING = 'PENDING'
    DONE = 'DONE'
    ERROR = 'IN_ERROR'

    id = Column(Integer, primary_key=True)
    study_case_id = Column(Integer,
                           ForeignKey(f'{StudyCase.__tablename__}.id',
                                      ondelete="CASCADE",
                                      name='fk_study_case_allocation_study_case_id'),
                           nullable=False, unique=True, index=True)
    status = Column(String(64), unique=False, server_default='')
    kubernetes_pod_name = Column(String(128), index=False, unique=True, server_default=None)
    message = Column(Text, index=False, unique=False, nullable=True)
    creation_date = Column(DateTime(timezone=True), server_default=func.now())
    
    

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'id': self.id,
            'study_case_id': self.study_case_id,
            'status': self.status,
            'kubernetes_pod_name': self.kubernetes_pod_name,
            'message': self.message,
            'creation_date': self.creation_date
        }

class UserStudyPreference(db.Model):
    """UserStudyPreference class"""

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer,
                     ForeignKey(
                         f'{User.__tablename__}.id',
                         ondelete="CASCADE",
                         name='fk_user_study_preference_user_id'),
                     nullable=False)
    study_case_id = Column(Integer,
                           ForeignKey(
                               f'{StudyCase.__tablename__}.id',
                               ondelete="CASCADE",
                               name='fk_user_study_preference_study_case_id'),
                           nullable=False)
    preference = Column(TEXT, index=False, unique=False)

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'study_case_id': self.study_case_id,
            'preference': self.preference
        }


class UserStudyFavorite(db.Model):
    """UserStudyFavorite class"""

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer,
                     ForeignKey(
                         f'{User.__tablename__}.id',
                         ondelete="CASCADE",
                         name='fk_user_study_favorite_user_id'),
                     nullable=False)
    study_case_id = Column(Integer,
                           ForeignKey(
                               f'{StudyCase.__tablename__}.id',
                               ondelete="CASCADE",
                               name='fk_user_study_favorite_study_case_id'),
                           nullable=False)

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'study_case_id': self.study_case_id,
        }


class UserLastOpenedStudy(db.Model):
    """User (five) last studies opened class"""

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer,
                     ForeignKey(
                         f'{User.__tablename__}.id',
                         ondelete="CASCADE",
                         name='fk_user_study_last_opened_user_id'),
                     nullable=False)
    study_case_id = Column(Integer,
                           ForeignKey(
                               f'{StudyCase.__tablename__}.id',
                               ondelete="CASCADE",
                               name='fk_user_study_last_opened_study_case_id'),
                           nullable=False)
    opening_date = Column(DateTime(timezone=True), server_default=func.now())

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'study_case_id': self.study_case_id,
            'opening_date': self.opening_date
        }


class AccessRights(db.Model):
    MANAGER = 'Manager'
    CONTRIBUTOR = 'Contributor'
    COMMENTER = 'Commenter'
    RESTRICTED_VIEWER = 'Restricted Viewer'
    MEMBER = 'Member'
    OWNER = 'Owner'
    REMOVE = 'Remove'

    id = Column(Integer, primary_key=True)
    access_right = Column(String(64), index=True, unique=True)
    description = Column(String(128), index=False, unique=False)

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'id': self.id,
            'access_right': self.access_right,
            'description': self.description,
        }


class GroupAccessUser(db.Model):
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer,
                      ForeignKey(
                          f'{Group.__tablename__}.id',
                          ondelete="CASCADE",
                          name='fk_group_access_user_group_id'),
                      nullable=False)
    user_id = Column(Integer,
                     ForeignKey(
                         f'{User.__tablename__}.id',
                         ondelete="CASCADE",
                         name='fk_group_access_user_user_id'),
                     nullable=False)
    right_id = Column(Integer,
                      ForeignKey(
                          f'{AccessRights.__tablename__}.id',
                          ondelete="CASCADE",
                          name='fk_group_access_user_right_id'))

    __table_args__ = (
        UniqueConstraint('user_id', 'group_id'),
    )

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'id': self.id,
            'group_id': self.group_id,
            'user_id': self.user_id,
            'right_id': self.right_id,
        }


class GroupAccessGroup(db.Model):
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer,
                      ForeignKey(
                          f'{Group.__tablename__}.id',
                          ondelete="CASCADE",
                          name='fk_group_access_group_group_id'),
                      nullable=False)
    group_member_id = Column(Integer,
                             ForeignKey(
                                 f'{Group.__tablename__}.id',
                                 ondelete="CASCADE",
                                 name='fk_group_access_group_group_member_id'),
                             nullable=False)
    right_id = Column(Integer,
                      ForeignKey(
                          f'{AccessRights.__tablename__}.id',
                          ondelete="CASCADE",
                          name='fk_group_access_group_right_id'))
    group_members_ids = Column(Text, index=False, unique=False)

    __table_args__ = (
        UniqueConstraint('group_id', 'group_member_id'),
    )

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'id': self.id,
            'group_id': self.group_id,
            'group_member_id': self.group_member_id,
            'right_id': self.right_id,
            'group_members_ids': self.group_members_ids,
        }


class ProcessAccessUser(db.Model):
    SOURCE_FILE = "FILE"
    SOURCE_USER = "USER"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer,
                     ForeignKey(
                         f'{User.__tablename__}.id',
                         ondelete="CASCADE",
                         name='fk_process_access_user_user_id'),
                     nullable=False)
    process_id = Column(Integer,
                        ForeignKey(
                            f'{Process.__tablename__}.id',
                            ondelete="CASCADE",
                            name='fk_process_access_user_process_id'),
                        nullable=False)
    right_id = Column(Integer,
                      ForeignKey(
                          f'{AccessRights.__tablename__}.id',
                          ondelete="CASCADE",
                          name='fk_process_access_user_right_id'))
    source = Column(String(94), unique=False, server_default=SOURCE_USER)

    __table_args__ = (
        UniqueConstraint('user_id', 'process_id'),
    )

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'process_id': self.process_id,
            'right_id': self.right_id,
            'source': self.source,
        }


class ProcessAccessGroup(db.Model):
    SOURCE_FILE = "FILE"
    SOURCE_USER = "USER"
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer,
                      ForeignKey(
                          f'{Group.__tablename__}.id',
                          ondelete="CASCADE",
                          name='fk_process_access_group_group_id'),
                      nullable=False)
    process_id = Column(Integer,
                        ForeignKey(
                            f'{Process.__tablename__}.id',
                            ondelete="CASCADE",
                            name='fk_process_access_group_process_id'),
                        nullable=False)
    right_id = Column(Integer,
                      ForeignKey(
                          f'{AccessRights.__tablename__}.id',
                          ondelete="CASCADE",
                          name='fk_process_access_group_right_id'))
    source = Column(String(94), unique=False, server_default=SOURCE_USER)

    __table_args__ = (
        UniqueConstraint('group_id', 'process_id'),
    )

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'id': self.id,
            'group_id': self.group_id,
            'process_id': self.process_id,
            'right_id': self.right_id,
            'source': self.source,
        }


class StudyCaseAccessUser(db.Model):
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer,
                     ForeignKey(
                         f'{User.__tablename__}.id',
                         ondelete="CASCADE",
                         name='fk_study_case_access_user_user_id'),
                     nullable=False)
    study_case_id = Column(Integer,
                           ForeignKey(
                               f'{StudyCase.__tablename__}.id',
                               ondelete="CASCADE",
                               name='fk_study_case_access_user_study_case_id'),
                           nullable=False)
    right_id = Column(Integer,
                      ForeignKey(
                          f'{AccessRights.__tablename__}.id',
                          ondelete="CASCADE",
                          name='fk_study_case_access_user_right_id'))

    __table_args__ = (
        UniqueConstraint('user_id', 'study_case_id'),
    )

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'study_case_id': self.study_case_id,
            'right_id': self.right_id,
        }


class StudyCaseAccessGroup(db.Model):
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer,
                      ForeignKey(
                          f'{Group.__tablename__}.id',
                          ondelete="CASCADE",
                          name='fk_study_case_access_group_group_id'),
                      nullable=False)
    study_case_id = Column(Integer,
                           ForeignKey(
                               f'{StudyCase.__tablename__}.id',
                               ondelete="CASCADE",
                               name='fk_study_case_access_group_study_case_id'),
                           nullable=False)
    right_id = Column(Integer,
                      ForeignKey(
                          f'{AccessRights.__tablename__}.id',
                          ondelete="CASCADE",
                          name='fk_study_case_access_group_right_id'))

    __table_args__ = (
        UniqueConstraint('group_id', 'study_case_id'),
    )

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'id': self.id,
            'group_id': self.group_id,
            'study_case_id': self.study_case_id,
            'right_id': self.right_id,
        }


class Notification(db.Model):
    """Notification class"""
    id = Column(Integer, primary_key=True)
    study_case_id = Column(Integer,
                           ForeignKey(
                               f'{StudyCase.__tablename__}.id',
                               ondelete="CASCADE",
                               name='fk_notification_study_case_id'))
    author = Column(String(94), index=True, unique=False)
    type = Column(String(64), index=True, unique=False)
    message = Column(String(255), unique=False)
    created = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'id': self.id,
            'study_case_id': self.study_case_id,
            'author': self.author,
            'type': self.type,
            'message': self.message,
            'created': self.created
        }


class StudyCaseChange(db.Model):
    """StudyCaseChanges class"""

    CSV_CHANGE = 'csv'
    SCALAR_CHANGE = 'scalar'

    id = Column(Integer, primary_key=True)
    notification_id = Column(Integer,
                             ForeignKey(
                                 f'{Notification.__tablename__}.id',
                                 ondelete="CASCADE",
                                 name='fk_study_case_change_notification_id'))
    variable_id = Column(Text, index=False, unique=False)
    variable_type = Column(String(64), index=True, unique=False)
    change_type = Column(String(64), index=True, unique=False)
    new_value = Column(Text, index=False, unique=False)
    old_value = Column(Text, index=False, unique=False)
    old_value_blob = Column(LargeBinary().with_variant(LONGBLOB, "mysql"), index=False, unique=False)
    last_modified = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_columns = Column(TEXT, index=False, unique=False)

    def serialize(self):
        """ json serializer for dto purpose
        """

        return {
            'id': self.id,
            'notification_id': self.notification_id,
            'variable_id': self.variable_id,
            'variable_type': self.variable_type,
            'change_type': self.change_type,
            'new_value': self.new_value,
            'old_value': self.old_value,
            'old_value_blob': True if self.old_value_blob is not None else False,
            'last_modified': self.last_modified,
            'deleted_columns': self.deleted_columns
        }


class StudyCoeditionUser(db.Model):
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer,
                     ForeignKey(
                         f'{User.__tablename__}.id',
                         ondelete="CASCADE",
                         name='fk_study_coedition_user_user_id'))
    study_case_id = Column(Integer,
                           ForeignKey(
                               f'{StudyCase.__tablename__}.id',
                               ondelete="CASCADE",
                               name='fk_study_coedition_user_study_case_id'))

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'study_case_id': self.study_case_id,
        }


class StudyCaseExecution(db.Model):
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    FINISHED = 'FINISHED'
    FAILED = 'FAILED'
    STOPPED = 'STOPPED'
    NOT_EXECUTED = 'NOT EXECUTED'

    EXECUTION_TYPE_K8S = 'KUBERNETES'
    EXECUTION_TYPE_PROCESS = 'PROCESS'

    id = Column(Integer, primary_key=True)
    study_case_id = Column(Integer,
                           ForeignKey(
                               f'{StudyCase.__tablename__}.id',
                               ondelete="CASCADE",
                               name='fk_study_case_execution_study_case_id'))
    execution_status = Column(String(64), index=True, unique=False, server_default=FINISHED)
    execution_type = Column(String(64), index=True, unique=False, server_default='')
    kubernetes_pod_name = Column(String(128), index=False, unique=False, server_default='')
    process_identifier = Column(Integer, index=False, unique=False)
    creation_date = Column(DateTime(timezone=True), server_default=func.now())
    requested_by = Column(String(64), index=True, unique=False, server_default='', nullable=False)
    cpu_usage = Column(String(32), index=False, unique=False, server_default='----', nullable=True)
    memory_usage = Column(String(32), index=False, unique=False, server_default='----', nullable=True)

    def serialize(self):
        """ json serializer for dto purpose
            data manager attribute is not serialize because is is intended to be only server side data
        """
        return {
            'id': self.id,
            'study_case_id': self.study_case_id,
            'execution_status': self.execution_status,
            'execution_type': self.execution_type,
            'kubernetes_pod_name': self.kubernetes_pod_name,
            'process_identifier': self.process_identifier,
            'creation_date': self.creation_date,
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage
        }


class StudyCaseDisciplineStatus(db.Model):
    """
        Class design to store discipline status during execution
    """
    id = Column(Integer, primary_key=True)
    study_case_id = Column(Integer,
                           ForeignKey(
                               f'{StudyCase.__tablename__}.id',
                               ondelete="CASCADE",
                               name='fk_study_case_discipline_status_study_case_id'))
    study_case_execution_id = Column(Integer,
                                     ForeignKey(
                                         f'{StudyCaseExecution.__tablename__}.id',
                                         ondelete="CASCADE",
                                         name='fk_study_case_discipline_status_study_case_execution_id'))
    discipline_key = Column(Text, index=False, unique=False)
    status = Column(String(64), index=False, unique=False)

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'id': self.id,
            'study_case_id': self.study_case_id,
            'study_case_execution_id': self.study_case_execution_id,
            'discipline_key': self.discipline_key,
            'status': self.status
        }


class StudyCaseLog(db.Model):
    id = Column(Integer, primary_key=True)
    study_case_id = Column(Integer,
                           ForeignKey(
                               f'{StudyCase.__tablename__}.id',
                               ondelete="CASCADE",
                               name='fk_study_case_log_study_case_id'))
    name = Column(Text, index=False, unique=False)
    log_level_name = Column(String(64), index=False, unique=False)
    created = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    message = Column(Text, index=False, unique=False)
    exception = Column(Text, index=False, unique=False)

    def serialize(self):
        """ json serializer for dto purpose
        """

        return {
            'name': self.name,
            'level': self.log_level_name,
            'created': self.created,
            'message': self.message,
            'exception': self.exception
        }


class StudyCaseExecutionLog(db.Model):
    id = Column(Integer, primary_key=True)
    study_case_id = Column(Integer,
                           ForeignKey(
                               f'{StudyCase.__tablename__}.id',
                               ondelete="CASCADE",
                               name='fk_study_case_execution_log_study_case_id'))
    study_case_execution_id = Column(Integer,
                                     ForeignKey(
                                         f'{StudyCaseExecution.__tablename__}.id',
                                         ondelete="CASCADE",
                                         name='fk_study_case_execution_log_study_case_execution_id'),
                                     nullable=True)
    name = Column(Text, index=False, unique=False)
    log_level_name = Column(String(64), index=False, unique=False)
    created = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    message = Column(Text, index=False, unique=False)
    exception = Column(Text, index=False, unique=False)

    def serialize(self):
        """ json serializer for dto purpose
        """

        return {
            'name': self.name,
            'level': self.log_level_name,
            'created': self.created,
            'message': self.message,
            'exception': self.exception
        }


class StudyCaseValidation(db.Model):
    VALIDATED = 'Validated'
    NOT_VALIDATED = 'Invalidated'

    id = Column(Integer, primary_key=True)
    study_case_id = Column(Integer,
                           ForeignKey(
                               f'{StudyCase.__tablename__}.id',
                               ondelete="CASCADE",
                               name='fk_study_case_validation_study_case_id'))
    namespace = Column(Text, index=False, unique=False)
    validation_comment = Column(Text, index=False, unique=False)
    validation_state = Column(String(64), index=False, unique=False)
    validation_date = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    validation_user = Column(Text, index=False, unique=False)
    validation_user_department = Column(String(64), index=False, unique=False)

    def serialize(self):
        """ json serializer for dto purpose
            datamanager attribute is not serialize because is is intended to be only server side data
        """

        return {
            'study_case_id': self.study_case_id,
            'namespace': self.namespace,
            'validation_comment': self.validation_comment,
            'validation_state': self.validation_state,
            'validation_date': self.validation_date,
            'validation_user': self.validation_user,
            'validation_user_department': self.validation_user_department
        }


class ReferenceStudy(db.Model):
    """Reference class"""

    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    FINISHED = 'FINISHED'
    FAILED = 'FAILED'
    UNKNOWN = 'NOT GENERATED'
    TYPE_USECASE_DATA = 'UsecaseData'
    TYPE_REFERENCE = 'Reference'

    id = Column(Integer, primary_key=True)
    process_id = Column(Integer,
                        ForeignKey(
                            f'{Process.__tablename__}.id',
                            ondelete="CASCADE",
                            name='fk_reference_study_process_id'))
    name = Column(String(128), index=True, unique=False)
    reference_path = Column(String(256), index=True, unique=False)
    reference_type = Column(String(128), index=True, unique=False)
    creation_date = Column(DateTime(timezone=True), nullable=True)
    execution_status = Column(String(64), index=True, unique=False, server_default=FINISHED)
    generation_logs = Column(Text, index=False, unique=False)
    kubernete_pod_name = Column(String(128), index=False, unique=False, server_default='')
    disabled = Column(Boolean, default=False, nullable=False)

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'id': self.id,
            'process_id': self.process_id,
            'name': self.name,
            'reference_path': self.reference_path,
            'reference_type': self.reference_type,
            'creation_date': self.creation_date,
            'execution_status': self.execution_status,
            'generation_logs': self.generation_logs,
            'kubernete_pod_name': self.kubernete_pod_name,
            'disabled': self.disabled
        }


class ReferenceStudyExecutionLog(db.Model):
    id = Column(Integer, primary_key=True)
    reference_id = Column(Integer,
                          ForeignKey(
                              f'{ReferenceStudy.__tablename__}.id',
                              ondelete="CASCADE",
                              name='fk_reference_study_execution_log_reference_id'))
    name = Column(Text, index=False, unique=False)
    log_level_name = Column(String(64), index=False, unique=False)
    created = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    message = Column(Text, index=False, unique=False)
    exception = Column(Text, index=False, unique=False)

    def serialize(self):
        """ json serializer for dto purpose
        """

        return {
            'name': self.name,
            'level': self.log_level_name,
            'created': self.created,
            'message': self.message,
            'exception': self.exception
        }


class Link(db.Model):
    """Link class"""

    id = Column(Integer, primary_key=True)
    url = Column(String(512), index=True, nullable=False)
    label = Column(String(64), index=False, nullable=False)
    description = Column(String(300), index=False, nullable=False)
    user_id = Column(Integer, ForeignKey(f'{User.__tablename__}.id', name='fk_link_user_id'), nullable=True)
    last_modified = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def serialize(self):
        """ json serializer for dto purpose
        """

        return {
            'id': self.id,
            'url': self.url,
            'label': self.label,
            'description': self.description,
            'user_id': self.user_id,
            'last_modified': self.last_modified
        }


class OAuthState(db.Model):
    """Link class"""

    id = Column(Integer, primary_key=True)
    is_active = Column(Boolean, default=False)
    is_invalidated = Column(Boolean, default=False)
    state = Column(String(64), index=False, nullable=False)
    creation_date = Column(DateTime(timezone=True), server_default=func.now())
    check_date = Column(DateTime(timezone=True), server_default=None, nullable=True)

    def serialize(self):
        """ json serializer for dto purpose
        """

        return {
            'id': self.id,
            'is_active': self.is_active,
            'is_invalidated': self.is_invalidated,
            'state': self.state,
            'creation_date': self.creation_date,
            'check_date': self.check_date
        }


class News(db.Model):
    """
        Class that register news about application
    """
    id = Column(Integer, primary_key=True)
    message = Column(String(300), index=False, unique=False)
    user_id = Column(Integer, ForeignKey(f'{User.__tablename__}.id', name='fk_news_user_id'), nullable=True)
    creation_date = Column(DateTime(timezone=True), server_default=func.now())
    last_modification_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)

    def serialize(self):
        """ json serializer for dto purpose
        """

        return {
            'id': self.id,
            'message': self.message,
            'user_id': self.user_id,
            'creation_date': self.creation_date,
            'last_modification_date': self.last_modification_date
        }


class Device(db.Model):
    """
    Class that allow to manage API access (non user access)
    """

    id = db.Column(Integer, primary_key=True)
    device_name = Column(String(80))
    device_key = Column(String(80))
    group_id = db.Column(Integer, ForeignKey(f'{Group.__tablename__}.id', ondelete="CASCADE", name='fk_device_group_id'))

    def __init__(self):
        self.device_key = Device.create_key()

    def serialize(self):
        """
        json serializer for dto purpose
        """
        return {
            'id': self.id,
            'device_name': self.device_name,
            'device_key': self.device_key,
            'group_id': self.group_id
        }

    def __repr__(self):
        """
        serialize for log purpose this class
        :return:  str
        """

        builder = [
            f'id: {self.id}',
            f'device_name: {self.device_name}',
            f'device_key: {self.device_key}',
            f'group_id: {self.group_id}'
        ]

        return '\n'.join(builder)

    @staticmethod
    def create_key():
        return uuid.uuid4().hex

