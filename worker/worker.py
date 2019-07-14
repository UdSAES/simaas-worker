#! /usr/bin/python3
# -*- coding: utf8 -*-

import numpy as np
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

    df = pd.DataFrame(ts[0])

    for series in ts[1:]:
        df = df.join(series)

    # Ensure that seconds relative to offset are used as index
    offset = df.index.min()
    df['time_rel'] = df.index
    df['time_rel'] = df['time_rel'].apply(lambda x: float((x - offset)/1000))
    df.set_index('time_rel', inplace=True)
    df.index.rename('time', inplace=True)

    # Replace NaN with constant value
    df.fillna(value=FILLNA, inplace=True)

    # Transform into np.ndarray with correct dtypes
    ndarray = np.array(df.to_records())

    return ndarray
