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
from sos_trades_api.models.custom_json_encoder import CustomJsonEncoder
from _datetime import datetime

from pandas import DataFrame, Index, Series
import numpy as np


class CustomJsonEncoderWithDatas(CustomJsonEncoder):
    def default(self, o):  # pylint: disable=E0202

        if isinstance(o, DataFrame):
            return o.to_json()
        elif isinstance(o, np.ndarray):
            return o.tolist()

        # default, if not one of the specified object. Caller's problem if this is not
        # serializable.
        return CustomJsonEncoder.default(self, o)
