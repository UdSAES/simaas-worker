#! /usr/bin/python3
# -*- coding: utf8 -*-

import os

from worker import logger, simulate_fmu2_cs

from .celery import app


@app.task
def simulate(req_body):
    # Retrieve FMU that implements the desired model instance
    pass

    # Simulate the model instance for the given input and record the result
    df = simulate_fmu2_cs(fmu, req_body, req_id=None)
    logger.debug(f"df\n{df}")

    # Perform post-processing if necessary
    pass

    # Format result and return (MUST be serializable as JSON)
    data_as_json = {}

    return data_as_json
