#! /usr/bin/python3
# -*- coding: utf8 -*-

import pandas as pd
from loguru import logger


def timeseries_dict_to_pd_series(ts_dict):
    """
    Turn timeseries object v1.3.0 into pd.Series.

    Input schema defined in /schemata/timeseries/schema_v1.3.0-oas2.json
    at https://github.com/UdSAES/designetz_schemata.
    The data is not changed, just represented differently!
    """

