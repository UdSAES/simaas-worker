#! /usr/bin/python3
# -*- coding: utf8 -*-

import fmpy
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

    for obj in ts_dict['timeseries']:
        timestamps.append(obj['timestamp'])
        values.append(obj['value'])

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


def simulate_fmu2_cs(fmu_filepath, options, req_id=None):
    """Simulate FMU 2.0 for CS, return result as pd.DataFrame."""

    # Prepare input data
    input_timeseries = []
    input_units = []
    for ts_obj in options['inputTimeseries']:
        input_timeseries.append(timeseries_dict_to_pd_series(ts_obj))
        input_units.append(ts_obj['unit'])
    start_time = options['simulationParameters']['startTime']
    stop_time = options['simulationParameters']['stopTime']
    relative_tolerance = 10e-5
    output_interval = options['simulationParameters']['outputInterval']
    input_ts = prepare_bc_for_fmpy(input_timeseries, input_units)
    start_values = dict(epochOffset=start_time/1000)

    # Execute simulation
    # NOTE: inside the FMU, time is represented in seconds starting at zero!
    sim_result = fmpy.simulate_fmu(
        fmu_filepath,
        validate=True,
        start_time=0,
        stop_time=int((stop_time - start_time)/1000),
        relative_tolerance=relative_tolerance,
        output_interval=output_interval,
        start_values=start_values,
        apply_default_start_values=True,
        input=input_ts,
        output=None
    )

    # Return simulation result as pd.DataFrame
    df = pd.DataFrame(sim_result)
    df['time'] = df['time']*1000 + start_time
    df.set_index(pd.DatetimeIndex(df['time']*10**6).tz_localize('utc'), inplace=True)
    del df['time']

    return df
