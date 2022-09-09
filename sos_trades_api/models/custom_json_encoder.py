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
Class overlad defaut json encoder to manage our class
"""
from flask.json import JSONEncoder
from _datetime import datetime

from pandas import DataFrame, Index, Series
import numpy as np

from sos_trades_api.models.access_rights_selectable import AccessRightsSelectable
from sos_trades_core.execution_engine.namespace import Namespace
from sos_trades_core.tools.post_processing.tables.table_style import TableStyles
from sos_trades_core.tools.post_processing.charts.chart_filter import ChartFilter
from sos_trades_core.tools.post_processing.tables.instanciated_table import InstanciatedTable
from sos_trades_core.tools.post_processing.charts.two_axes_instanciated_chart import TwoAxesInstanciatedChart
from sos_trades_core.tools.post_processing.plotly_native_charts.instantiated_plotly_native_chart import InstantiatedPlotlyNativeChart


from sos_trades_api.models.loaded_group import LoadedGroup
from sos_trades_api.models.entity_rights import EntityRight, \
    ProcessEntityRights, EntityRights, GroupEntityRights, StudyCaseEntityRights
from sos_trades_api.models.loaded_process import LoadedProcess
from sos_trades_api.models.loaded_study_case import LoadedStudyCase
from sos_trades_api.models.study_notification import StudyNotification
from sos_trades_api.models.calculation_dashboard import CalculationDashboard
from sos_trades_api.models.user_application_right import UserApplicationRight
from sos_trades_api.models.model_status import ModelStatus
from sos_trades_api.models.database_models import StudyCase, Group, User, GroupAccessUser, \
    StudyCaseExecutionLog, ReferenceStudy, StudyCaseValidation, Link, StudyCaseAllocation, News
from sos_trades_api.models.database_models import UserProfile, StudyCaseChange, AccessRights,StudyCaseLog
from sos_trades_api.models.loaded_study_case_execution_status import LoadedStudyCaseExecutionStatus
from sos_trades_api.models.study_case_dto import StudyCaseDto
from sos_trades_core.tools.post_processing.post_processing_bundle import PostProcessingBundle


class CustomJsonEncoder(JSONEncoder):
    def default(self, o):  # pylint: disable=E0202

        if isinstance(o, LoadedStudyCase):
            return o.serialize()
        elif isinstance(o, StudyNotification):
            return o.serialize()
        elif isinstance(o, AccessRightsSelectable):
            return o.serialize()
        elif isinstance(o, ModelStatus):
            return o.serialize()
        elif isinstance(o, ReferenceStudy):
            return o.serialize()
        elif isinstance(o, EntityRights):
            return o.serialize()
        elif isinstance(o, StudyCaseLog):
            return o.serialize()
        elif isinstance(o, EntityRight):
            return o.serialize()
        elif isinstance(o, LoadedProcess):
            return o.serialize()
        elif isinstance(o, StudyCaseChange):
            return o.serialize()
        elif isinstance(o, StudyCaseValidation):
            return o.serialize()
        elif isinstance(o, UserApplicationRight):
            return o.serialize()
        elif isinstance(o, CalculationDashboard):
            return o.serialize()
        elif isinstance(o, LoadedGroup):
            return o.serialize()
        elif isinstance(o, GroupAccessUser):
            return o.serialize()
        elif isinstance(o, User):
            return o.serialize()
        elif isinstance(o, UserProfile):
            return o.serialize()
        elif isinstance(o, Group):
            return o.serialize()
        elif isinstance(o, StudyCase):
            return o.serialize()
        elif isinstance(o, LoadedStudyCaseExecutionStatus):
            return o.serialize()
        elif isinstance(o, Link):
            return o.serialize()
        elif isinstance(o, StudyCaseAllocation):
            return o.serialize()
        elif isinstance(o, News):
            return o.serialize()
        elif isinstance(o, DataFrame):
            return '://dataframe'
        elif isinstance(o, Index):
            return '://index'
        elif isinstance(o, np.ndarray):
            return '://ndarray'
        elif isinstance(o, Series):
            return list(o)
        elif isinstance(o, type):
            return str(o).lower()
        elif isinstance(o, TwoAxesInstanciatedChart):
            return o.to_dict()
        elif isinstance(o, InstanciatedTable):
            return o.to_dict()
        elif isinstance(o, TableStyles):
            return o.to_dict()
        elif isinstance(o, ChartFilter):
            return o.to_dict()
        elif isinstance(o, np.integer):
            return int(o)
        elif isinstance(o, np.float):
            return float(o)
        elif isinstance(o, np.complex):
            return o.real
        elif isinstance(o, datetime):
            return str(o)
        elif isinstance(o, np.dtype):
            return str(o)
        elif isinstance(o, StudyCaseExecutionLog):
            return o.serialize()
        elif isinstance(o, Namespace):
            return o.to_dict()
        elif isinstance(o, StudyCaseDto):
            return o.serialize()
        elif isinstance(o, AccessRights):
            return o.serialize()
        elif isinstance(o, StudyCaseEntityRights):
            return o.serialize()
        elif isinstance(o, ProcessEntityRights):
            return o.serialize()
        elif isinstance(o, GroupEntityRights):
            return o.serialize()
        elif isinstance(o, PostProcessingBundle):
            return o.to_dict()
        elif isinstance(o, InstantiatedPlotlyNativeChart):
            return o.to_plotly_dict()
        elif isinstance(o, set):
            return list(o)

        # default, if not one of the specified object. Caller's problem if this is not
        # serializable.
        return JSONEncoder.default(self, o)
