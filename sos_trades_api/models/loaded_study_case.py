'''
Copyright 2022 Airbus SAS

Modifications on 29/04/2024 Copyright 2024 Capgemini
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

from sostrades_core.execution_engine.proxy_discipline import ProxyDiscipline
from sqlalchemy import and_

from sos_trades_api.models.database_models import (
    StudyCase,
    StudyCoeditionUser,
    UserStudyPreference,
)
from sos_trades_api.models.study_case_dto import StudyCaseDto
from sos_trades_api.server.base_server import app, db
from sos_trades_api.tools.chart_tools import load_post_processing

"""
Class that represent a study case with its logical treeview loaded
"""

class LoadStatus:
    NONE = "none"
    IN_PROGESS = "in_progress"
    READ_ONLY_MODE = "read_only_mode"
    LOADED = "loaded"
    IN_ERROR = "in_error"


class LoadedStudyCase:

    def __init__(self, study_case_manager, no_data, read_only, user_id, load_post_processings=False):

        self.study_case = StudyCaseDto(study_case_manager.study)

        self.load_status = study_case_manager.load_status
        self.preference = {}
        self.no_data = no_data
        self.read_only = read_only
        self.treenode = {}
        self.study_case.execution_status = ""
        self.post_processings = {}
        self.plotly = {}
        self.n2_diagram = {}
        self.can_reload = study_case_manager.check_study_can_reload()
        self.dashboard = {}

        if user_id is not None:
            self.user_id_execution_authorized = self.__load_user_execution_authorised(
                user_id)
        else:
            self.user_id_execution_authorized = 0

        if self.load_status == LoadStatus.LOADED:
            self.load_treeview_and_post_proc(
                study_case_manager, no_data, read_only, user_id, load_post_processings)

    def load_treeview_and_post_proc(self, study_case_manager, no_data, read_only, user_id, load_post_proc):
        study_case_manager.execution_engine.dm.treeview = None

        treeview = study_case_manager.execution_engine.get_treeview(
            no_data, read_only)
        self.n2_diagram = {}

        if treeview is not None:
            self.treenode = treeview.to_dict()
        self.post_processings = {}
        self.plotly = {}
        self.n2_diagram = study_case_manager.n2_diagram
        self.__load_user_study_preference(user_id)

        # Loading charts if study is finished
        if study_case_manager.execution_engine.root_process.status == ProxyDiscipline.STATUS_DONE:
            # Get discipline filters
            self.post_processings = load_post_processing(
                study_case_manager.execution_engine, load_post_proc)

    def __load_user_study_preference(self, user_id):
        """
        Load study preferences for the given user
        :params: user_id, user identification of the preferences
        :type: integer
        """
        if user_id is not None:
            with app.app_context():
                preferences = UserStudyPreference.query.filter(
                    and_(UserStudyPreference.user_id == user_id, UserStudyPreference.study_case_id == self.study_case.id)).all()

                if len(preferences) > 0:
                    for preference in preferences:
                        panel_id = preference.panel_identifier
                        panel_opened = preference.panel_opened
                        self.preference[panel_id] = panel_opened

    def __load_user_execution_authorised(self, user_id):
        """
        Load user authorised for execution
        :params: user_id, user identification of the preferences
        :type: integer
        """
        # Retrieve study case with user authorised for execution
        study_case_loaded = StudyCase.query.filter(
            StudyCase.id == self.study_case.id).first()

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
            # A user is declared as authorised, check if he is connected in
            # coedition room
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
        """
        json serializer for dto purpose
        """
        return {
            "study_case": self.study_case,
            "treenode": self.treenode,
            "post_processings": self.post_processings,
            "plotly": self.plotly,
            "n2_diagram": self.n2_diagram,
            "user_id_execution_authorized": self.user_id_execution_authorized,
            "no_data": self.no_data,
            "read_only": self.read_only,
            "preference": self.preference,
            "can_reload": self.can_reload,
            "load_status": self.load_status,
            "dashboard": self.dashboard,

        }
