#! /usr/bin/python3
# -*- coding: utf8 -*-

import pandas as pd
from loguru import logger


FILLNA = 0


def timeseries_dict_to_pd_series(ts_dict):
    """
    Turn timeseries object v1.3.0 into sorted pd.Series.

    Input schema defined in /schemata/timeseries/schema_v1.3.0-oas2.json
    at https://github.com/UdSAES/designetz_schemata.
    The data is not changed, just represented differently!
    """

    timestamps = []
    values = []

    for array in ts_dict['timeseries']:
        timestamps.append(array[0])
        values.append(array[1])

    s = pd.Series(values, index=timestamps, name=ts_dict['label'])
    s.sort_index(inplace=True)

    return s


def prepare_bc_for_fmpy(ts, units=None):
    """Turn array of pd.Series into correctly shaped np.ndarray."""

    pass
