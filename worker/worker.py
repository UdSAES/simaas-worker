#! /usr/bin/python3
# -*- coding: utf8 -*-

# SPDX-FileCopyrightText: 2021 UdS AES <https://www.uni-saarland.de/lehrstuhl/frey.html>
# SPDX-License-Identifier: MIT


import json
import os

import fmpy
import numpy as np
import pandas as pd
import pendulum
from jinja2 import Environment, FileSystemLoader
from pydash import py_

from . import logger

FILLNA = 0
ENV = Environment(
    loader=FileSystemLoader(os.environ["SIMWORKER_TMPFS_PATH"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def cast_to_type(var, type):
    if var == None:
        return var
    else:
        if type == "Real":
            return float(var)
        if type == "Integer":
            return int(var)
        if type == "Enumeration":
            raise NotImplementedError("type 'Enumeration' is not yet supported")
        if type == "Boolean":
            return bool(var)
        if type == "String":
            return str(var)


def scalar_variable_as_obj(x):
    type_map = {
        "Real": "number",
        "Integer": "integer",
        "Enumeration": "Enumeration",
        "Boolean": "boolean",
        "String": "string",
    }

    obj = {
        "name": py_.split(x.name, ".")[-1],
        # "valueReference": x.valueReference,
        "description": x.description,
        "type": type_map[x.type],
        # "dimensions": x.dimensions,
        # "dimensionValueReferences": x.dimensionValueReferences,
        "quantitiy": x.quantitiy,
        "unit": x.unit,
        # "displayUnit": x.displayUnit,
        # "relativeQuantity": x.relativeQuantity,
        "min": cast_to_type(x.min, x.type),
        "max": cast_to_type(x.max, x.type),
        "nominal": cast_to_type(x.nominal, x.type),
        # "unbounded": x.unbounded,
        "start": cast_to_type(x.start, x.type),
        # "derivative": x.derivative,
        # "causality": x.causality,
        # "variability": x.variability,
        # "initial": x.initial,
        # "reinit": x.reinit,
        # "sourceline": x.sourceline,
    }

    if x.declaredType is not None:
        for q in [a for a in dir(x.declaredType) if not a.startswith("__")]:
            k = q.__str__()
            v = getattr(x.declaredType, q)

            if k in obj:
                if (obj[k] == None) and (v != None):
                    if k in ["min", "max", "nominal", "start"]:
                        obj[k] = cast_to_type(v, x.declaredType.type)
                    else:
                        obj[k] = v

    if obj["unit"] is None:
        obj["unit"] = 1

    return py_.pick_by(obj, lambda x: x is not None)


def render_template(template_path, objects):
    template = ENV.get_template(template_path)
    required = []
    for obj in objects:
        if not py_.has(obj, "start"):
            required.append(obj["name"])
    return template.render(data=objects, required=required)


def parse_model_description(md_path, template_parameters, template_io, records):
    """
    Parse `modelDescription.xml` and derive schemata.

    Reads the model description and derives JSON-schemata
    for parameterization/inputs/outputs to be embedded in
    the OpenAPI-Specification of the API.
    """

    def find_model_parameters(x, record_component_names):
        a = False
        for name in record_component_names:
            a |= py_.starts_with(x.name, name)

        return a

    # Read the model description using FMPy
    md = fmpy.read_model_description(md_path)

    # Fill in basic properties of FMU
    parsed = {
        "guid": md.guid[1:-1],  # strip curly braces by slicing the string
        "fmiVersion": md.fmiVersion,
        "modelName": md.modelName,
        "description": md.description,
        "generationTool": md.generationTool,
        "generationDateAndTime": md.generationDateAndTime,
        "schemata": {},
    }

    # Derive the desired JSON schema objects
    jobs = [
        {
            "name": "parameter",
            "selector": lambda x: find_model_parameters(x, records),
            "template": os.path.basename(template_parameters),
        },
        {
            "name": "input",
            "selector": lambda x: x.causality == "input",
            "template": os.path.basename(template_io),
        },
        {
            "name": "output",
            "selector": lambda x: x.causality == "output",
            "template": os.path.basename(template_io),
        },
    ]

    for job in jobs:
        # Filter model variables
        scalar_variables = py_.filter(md.modelVariables, job["selector"])

        # Represent each `ScalarVariable`-instance as dictionary
        objects = []
        for var in scalar_variables:
            objects.append(scalar_variable_as_obj(var))

        # Render schema from template
        schema = render_template(job["template"], objects)
        parsed["schemata"][job["name"]] = json.loads(schema)

    return parsed


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


def simulate_fmu2_cs(fmu_filepath, parameter_set_filepath, options):
    """Simulate FMU 2.0 for CS, return result as pd.DataFrame."""

    # Ensure that logs can be correlated to requests
    req_id = options["requestId"]
    if req_id is not None:
        log = logger.bind(req_id=req_id)
    else:
        log = logger

    # Decide whether or not to apply an offset to the input time series
    input_time_is_relative = options["simulationParameters"]["inputTimeIsRelative"]

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
    # start_values = options["startValues"] if "startValues" in options.keys() else {}
    start_values = {
        "fileName": parameter_set_filepath,
    }

    if input_time_is_relative is False:
        start_values["epochOffset"] = offset / 1000

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
        fmi_call_logger=log.trace,
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


def df_to_repr_json(df, fmu, time_is_relative):
    """Render JSON-representation of DataFrame."""

    logger.trace("df:\n{}".format(df))

    # Read model description
    desc = fmpy.read_model_description(fmu)

    # Transform columns of dataframe to JSON-object
    data = []
    for cname in df.columns:
        # Find unit of quantity
        model_variable = py_.find(desc.modelVariables, lambda x: x.name == cname)
        if model_variable.unit is not None:
            unit = model_variable.unit
        else:
            unit = "1"

        # Transform dataframe to timeseries-object
        ts_value_objects = json.loads(
            df[cname]
            .to_json(orient="table")
            .replace("time", "timestamp")
            .replace(cname, "value")
        )["data"]
        if time_is_relative is False:
            for x in ts_value_objects:
                x["datetime"] = pendulum.parse(x["timestamp"]).isoformat()
                x["timestamp"] = int(pendulum.parse(x["timestamp"]).format("x"))

        # Join label, unit and data
        data.append(
            {
                "label": cname,
                "unit": unit,
                "timeseries": ts_value_objects,
            }
        )

    # Return JSON-representation of entire dataframe _without_ additional content
    return data
