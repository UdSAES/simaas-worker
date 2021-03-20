#! /usr/bin/python3
# -*- coding: utf8 -*-

import os

import pydash
import requests
import scipy.io as sio

from worker import df_to_repr_json, logger, simulate_fmu2_cs, strtobool

from .celery import app

# Specify directories in which to store temporary files
tmp_dir = os.environ["SIMWORKER_TMPFS_PATH"]

# Use global objects as local lookup table
model_instances = {}


# Helper functions
def get_fmu_filepath(model_href):
    """Get filepath of model as FMU."""

    filepath = os.path.join(
        tmp_dir,
        model_href.split("/")[-2],
        model_href.split("/")[-1],
    )

    # Iff .fmu-file doesn't exist locally, download it
    if not os.path.isfile(filepath):
        # Prepare directory
        dirname = os.path.dirname(filepath)
        if not os.path.isdir(dirname):
            os.mkdir(dirname)

        # Download and save file
        r = requests.get(model_href)
        with open(filepath, "w+b") as fp:
            fp.write(r.content)

    # Return local path to previously downloaded file
    return filepath


def get_parameter_set_filepath(task_rep):
    """Get filepath of parameter set as .mat-file."""

    instance_id = task_rep["modelInstanceId"]

    # Iff the parameter set is new, save it as .mat-file
    if not pydash.has(model_instances, instance_id):
        # Throw away units/only keep values
        parameters = {}
        for key, value in task_rep["parameterSet"].items():
            parameters[key] = value["value"]

        # Write parameter values to .mat-file
        filepath = os.path.join(tmp_dir, instance_id + ".mat")
        sio.savemat(filepath, parameters, format="4")
        model_instances[instance_id] = filepath

    # Return local path to parameter set as .mat-file
    return model_instances[instance_id]


# Actual tasks
@app.task
def simulate(task_rep):
    # Retrieve filepath of FMU
    fmu_path = get_fmu_filepath(task_rep["modelHref"])

    # Get path to .mat-file containing parameter set (=defining model instance)
    parameter_set_path = get_parameter_set_filepath(task_rep)

    # Simulate the model instance for the given input and record the result
    df = simulate_fmu2_cs(fmu_path, parameter_set_path, task_rep)
    logger.debug(f"df\n{df}")

    # Perform post-processing if necessary
    pass

    # Format result and return (MUST be serializable as JSON)
    input_time_is_relative = strtobool(
        task_rep["simulationParameters"]["inputTimeIsRelative"]
    )
    data_as_json = df_to_repr_json(df, fmu_path, input_time_is_relative)

    return data_as_json
