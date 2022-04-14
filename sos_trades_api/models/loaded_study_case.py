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
Class that represent a study case with its logical treeview loaded
"""
import os
from sos_trades_api.tools.chart_tools import load_post_processing
from sos_trades_core.execution_engine.sos_discipline import SoSDiscipline
import json
from sos_trades_api.models.database_models import UserStudyPreference, StudyCase, StudyCoeditionUser
from sqlalchemy import and_

from sos_trades_api.base_server import db, app

import time
from sos_trades_api.models.study_case_dto import StudyCaseDto


class LoadedStudyCase:

    def __init__(self, study_case_manager, no_data, read_only, user_id):

        self.study_case = StudyCaseDto(study_case_manager.study)
        self.load_in_progress = study_case_manager.load_in_progress
        self.preference = {}
        self.no_data = no_data
        self.read_only = read_only
        self.treenode = {}
        self.study_case.execution_status = ''
        self.post_processings = {}
        self.plotly = {}
        self.n2_diagram = {}
        self.can_reload = study_case_manager.check_study_can_reload()

        self.user_id_execution_authorized = self.__load_user_execution_authorised(user_id)

        if not self.load_in_progress:

            study_case_manager.execution_engine.dm.treeview = None
            
            treeview = study_case_manager.execution_engine.get_treeview(
                no_data, read_only)
            self.n2_diagram = {}

            if treeview is not None:
                self.study_case.execution_status = treeview.root.status
                self.treenode = treeview.to_dict()
            self.post_processings = {}
            self.plotly = {}
            self.n2_diagram = study_case_manager.n2_diagram
            self.__load_user_study_preference(user_id)

            # Loading charts if study is finished
            if study_case_manager.execution_engine.root_process.status == SoSDiscipline.STATUS_DONE:
                # Get discipline filters
                self.post_processings = load_post_processing(
                    study_case_manager.execution_engine, False)

    def __load_user_study_preference(self, user_id):
        """ Load study preferences for the given user
        :params: user_id, user identification of the preferences
        :type: integer
        """
        if user_id is not None:
            with app.app_context():
                preferences = UserStudyPreference.query.filter(
                    and_(UserStudyPreference.user_id == user_id, UserStudyPreference.study_case_id == self.study_case.id)).all()

                if len(preferences) > 0:
                    preference = preferences[0].preference

                    if len(preference) > 0:
                        self.preference = json.loads(preference)
                else:
                    new_preference = UserStudyPreference()
                    new_preference.user_id = user_id
                    new_preference.study_case_id = self.study_case.id
                    new_preference.preference = ''
                    db.session.add(new_preference)
                    db.session.commit()

    def __load_user_execution_authorised(self, user_id):
        """ Load user authorised for execution
        :params: user_id, user identification of the preferences
        :type: integer
        """
        # Retrieve study case with user authorised for execution
        study_case_loaded = StudyCase.query.filter(StudyCase.id == self.study_case.id).first()

        # Check a user is declared in study case with authorization
        if study_case_loaded.user_id_execution_authorised is None:
            # Add user to coedition room
            study_coedition = StudyCoeditionUser()
            study_coedition.study_case_id = self.study_case.id
            study_coedition.user_id = user_id
            db.session.add(study_coedition)
            db.session.commit()

            # Update Study case user id authorised
            study_case_loaded.user_id_execution_authorised = user_id
            db.session.add(study_case_loaded)
            db.session.commit()

            user_id_exec_auth = user_id
        else:
            # A user is declared as authorised, check if he is connected in coedition room
            user_coedition = StudyCoeditionUser.query.filter(
                StudyCoeditionUser.user_id == study_case_loaded.user_id_execution_authorised).filter(
                StudyCoeditionUser.study_case_id == self.study_case.id).first()

            if user_coedition is not None:
                # User authorised and connected to study no change
                user_id_exec_auth = study_case_loaded.user_id_execution_authorised
            else:
                # Add user to coedition room
                study_coedition = StudyCoeditionUser()
                study_coedition.study_case_id = self.study_case.id
                study_coedition.user_id = user_id
                db.session.add(study_coedition)
                db.session.commit()

                # Update Study case user id authorised
                study_case_loaded.user_id_execution_authorised = user_id
                db.session.add(study_case_loaded)
                db.session.commit()

                user_id_exec_auth = user_id

        return user_id_exec_auth

    def serialize(self):
        """ json serializer for dto purpose
        """
        return {
            'study_case': self.study_case,
            'treenode': self.treenode,
            'post_processings': self.post_processings,
            'plotly': self.plotly,
            'n2_diagram': self.n2_diagram,
            'user_id_execution_authorized': self.user_id_execution_authorized,
            'no_data': self.no_data,
            'read_only': self.read_only,
            'preference': self.preference,
            'load_in_progress': self.load_in_progress,
            'can_reload': self.can_reload
        }
