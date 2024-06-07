'''
Copyright 2022 Airbus SAS
Modifications on 2023/06/07-2023/11/03 Copyright 2023 Capgemini

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
from datetime import datetime

import numpy as np
from pandas import DataFrame, Index, Series
from simplejson import JSONEncoder
from sostrades_core.execution_engine.namespace import Namespace
from sostrades_core.tools.post_processing.charts.chart_filter import ChartFilter
from sostrades_core.tools.post_processing.charts.two_axes_instanciated_chart import (
    TwoAxesInstanciatedChart,
)
from sostrades_core.tools.post_processing.plotly_native_charts.instantiated_plotly_native_chart import (
    InstantiatedPlotlyNativeChart,
)
from sostrades_core.tools.post_processing.post_processing_bundle import (
    PostProcessingBundle,
)
from sostrades_core.tools.post_processing.tables.instanciated_table import (
    InstanciatedTable,
)
from sostrades_core.tools.post_processing.tables.table_style import TableStyles

from sos_trades_api.models.access_rights_selectable import AccessRightsSelectable
from sos_trades_api.models.calculation_dashboard import CalculationDashboard
from sos_trades_api.models.database_models import (
    AccessRights,
    Group,
    GroupAccessUser,
    Link,
    News,
    PodAllocation,
    ReferenceStudy,
    StudyCase,
    StudyCaseChange,
    StudyCaseExecutionLog,
    StudyCaseLog,
    StudyCaseValidation,
    User,
    UserProfile,
)
from sos_trades_api.models.entity_rights import (
    EntityRight,
    EntityRights,
    GroupEntityRights,
    ProcessEntityRights,
    StudyCaseEntityRights,
)
from sos_trades_api.models.loaded_group import LoadedGroup
from sos_trades_api.models.loaded_process import LoadedProcess
from sos_trades_api.models.loaded_study_case import LoadedStudyCase
from sos_trades_api.models.loaded_study_case_execution_status import (
    LoadedStudyCaseExecutionStatus,
)
from sos_trades_api.models.model_status import ModelStatus
from sos_trades_api.models.study_case_dto import StudyCaseDto
from sos_trades_api.models.study_notification import StudyNotification
from sos_trades_api.models.user_application_right import UserApplicationRight
from sos_trades_api.models.user_dto import UserDto

"""
Class overlad defaut json encoder to manage our class
"""

class CustomJsonEncoder(JSONEncoder):
    def __init__(self, *args, **kwargs):
        kwargs["ignore_nan"] = True
        super().__init__(*args, **kwargs)

    def default(self, o):  # pylint: disable=E0202

        if isinstance(o, (AccessRightsSelectable, CalculationDashboard, EntityRight, EntityRights, Group, GroupAccessUser, Link, LoadedGroup, LoadedProcess, LoadedStudyCase, LoadedStudyCaseExecutionStatus, ModelStatus, News, PodAllocation, ReferenceStudy, StudyCase, StudyCaseChange, StudyCaseLog, StudyCaseValidation, StudyNotification, User, UserApplicationRight, UserDto, UserProfile)):
            return o.serialize()
        elif isinstance(o, DataFrame):
            return "://dataframe"
        elif isinstance(o, Index):
            return "://index"
        elif isinstance(o, np.ndarray):
            return "://ndarray"
        elif isinstance(o, Series):
            return list(o)
        elif isinstance(o, type):
            return str(o).lower()
        elif isinstance(o, (ChartFilter, InstanciatedTable, TableStyles, TwoAxesInstanciatedChart)):
            return o.to_dict()
        elif isinstance(o, np.integer):
            return int(o)
        elif isinstance(o, float):
            return float(o)
        elif isinstance(o, complex):
            return o.real
        elif isinstance(o, (datetime, np.dtype)):
            return str(o)
        elif isinstance(o, StudyCaseExecutionLog):
            return o.serialize()
        elif isinstance(o, Namespace):
            return o.to_dict()
        elif isinstance(o, (AccessRights, GroupEntityRights, ProcessEntityRights, StudyCaseDto, StudyCaseEntityRights)):
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
