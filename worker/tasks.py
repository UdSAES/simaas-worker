#! /usr/bin/python3
# -*- coding: utf8 -*-

import os

import requests
import scipy.io as sio
from cachetools import LRUCache, TTLCache, cached

from worker import df_to_repr_json, logger, simulate_fmu2_cs

from .celery import app

# Specify directories in which to store temporary files
tmp_dir = os.environ["SIMWORKER_TMPFS_PATH"]
cache_maxsize = int(os.environ["SIMWORKER_TMPFS_MAXSIZE"])

# Helper classes
class LRUCacheWithAssociatedFile(LRUCache):
    def popitem(self):
        instance_id, filepath = super().popitem()
        if os.path.isfile(filepath):
            os.remove(filepath)
        return instance_id, filepath


# Global cache object <- use tmpfs-mount with maximum size of cache
lru_cache_bounded_by_total_filesize = LRUCacheWithAssociatedFile(
    getsizeof=lambda x: os.stat(x).st_size,
    maxsize=cache_maxsize,
)

# Helper functions
@cached(cache=lru_cache_bounded_by_total_filesize)
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


@cached(
    cache=lru_cache_bounded_by_total_filesize,
    key=lambda x: x["modelInstanceId"],
)
def get_parameter_set_filepath(task_rep):
    """Get filepath of parameter set as .mat-file."""

    instance_id = task_rep["modelInstanceId"]

    # Throw away units/only keep values
    parameters = {}
    for key, value in task_rep["parameterSet"].items():
        parameters[key] = value["value"]

    # Write parameter values to .mat-file
    filepath = os.path.join(tmp_dir, instance_id + ".mat")
    sio.savemat(filepath, parameters, format="4")

    # Return local path to parameter set as .mat-file
    return filepath


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
    input_time_is_relative = task_rep["simulationParameters"]["inputTimeIsRelative"]
    data_as_json = df_to_repr_json(df, fmu_path, input_time_is_relative)

    return data_as_json
