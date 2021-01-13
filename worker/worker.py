#! /usr/bin/python3
# -*- coding: utf8 -*-

import distutils

import fmpy
import numpy as np
import pandas as pd
import pendulum

from . import logger

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

    for obj in ts_dict["timeseries"]:
        timestamps.append(obj["timestamp"])
        values.append(obj["value"])

    s = pd.Series(values, index=timestamps, name=ts_dict["label"])
    s.sort_index(inplace=True)

    return s


def prepare_bc_for_fmpy(ts, is_relative, offset=None):
    """Turn array of pd.Series into correctly shaped np.ndarray."""

    df = pd.DataFrame(ts[0])
    df = df.join(
        ts[1:], how="outer"
    )  # use how='outer' to not drop rows with missing values

    # Deal with missing values explicitly
    # TODO decide which method to use!
    # df.fillna(value=FILLNA, inplace=True)
    df.interpolate(method="linear", inplace=True)  # XXX interpolation!

    # Ensure that seconds relative to offset are used as index
    if is_relative == False:
        df["time_rel"] = df.index
        df["time_rel"] = df["time_rel"].apply(lambda x: float((x - offset) / 1000))
        df.set_index("time_rel", inplace=True)

    df.index.rename("time", inplace=True)

    # Transform into np.ndarray with correct dtypes
    ndarray = np.array(df.to_records())

    return ndarray


def simulate_fmu2_cs(fmu_filepath, options, req_id=None):
    """Simulate FMU 2.0 for CS, return result as pd.DataFrame."""
    input_time_is_relative = bool(
        distutils.util.strtobool(options["simulationParameters"]["inputTimeIsRelative"])
    )

    # Ensure that logs can be correlated to requests
    if req_id is not None:
        log = logger.bind(req_id=req_id)
    else:
        log = logger

    # Prepare input data
    input_timeseries = []
    input_units = []
    for ts_obj in options["inputTimeseries"]:
        input_timeseries.append(timeseries_dict_to_pd_series(ts_obj))
        input_units.append(ts_obj["unit"])

    if input_time_is_relative is True:
        start_time = options["simulationParameters"]["startTime"]
        stop_time = options["simulationParameters"]["stopTime"]
        offset = None
    else:
        start_time = 0
        stop_time = int(
            (
                options["simulationParameters"]["stopTime"]
                - options["simulationParameters"]["startTime"]
            )
            / 1000
        )
        offset = options["simulationParameters"]["startTime"]
    input_ts = prepare_bc_for_fmpy(input_timeseries, input_time_is_relative, offset)

    log.trace(f"start_time: {start_time}")
    log.trace(f"stop_time: {stop_time}")
    log.trace(f"offset: {offset}")
    log.trace(f"input_ts:\n{input_ts}")

    # Set simulation parameters
    relative_tolerance = 10e-5
    output_interval = options["simulationParameters"]["outputInterval"]

    # Ensure that start values are set as required
    start_values = options["startValues"] if "startValues" in options.keys() else {}

    # Execute simulation
    # -- inside the FMU, time is represented in seconds starting at zero!
    sim_result = fmpy.simulate_fmu(
        fmu_filepath,
        validate=True,
        start_time=start_time,
        stop_time=stop_time,
        relative_tolerance=relative_tolerance,
        output_interval=output_interval,
        start_values=start_values,
        apply_default_start_values=True,
        input=input_ts,
        # output=[
        #     'temperature', 'directHorizontalIrradiance', 'diffuseHorizontalIrradiance',
        #     'powerDC', 'totalEnergyDC'
        # ]  # TODO use list of all variables from modelDescription.xml?
    )

    # Return simulation result as pd.DataFrame
    df = pd.DataFrame(sim_result)
    log.trace(f"df\n{df}")

    if input_time_is_relative is True:
        df.set_index(pd.Index(df["time"], dtype="float"), inplace=True)
    else:
        df["time"] = df["time"] * 1000 + options["simulationParameters"]["startTime"]
        df.set_index(
            pd.DatetimeIndex(df["time"] * 10 ** 6).tz_localize("utc"), inplace=True
        )

        datetime_string_start = pendulum.from_timestamp(
            options["simulationParameters"]["startTime"] / 1000
        ).to_datetime_string()
        datetime_string_stop = pendulum.from_timestamp(
            options["simulationParameters"]["stopTime"] / 1000
        ).to_datetime_string()

        df = df[datetime_string_start:datetime_string_stop]

    del df["time"]

    log.trace(f"df\n{df}")

    return df
