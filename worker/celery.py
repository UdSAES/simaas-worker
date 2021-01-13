#! /usr/bin/python3
# -*- coding: utf8 -*-

import os
import sys

from celery import Celery

from worker import logger

EXIT_ENVVAR_MISSING = 1


# Ensure that all required ENVVARs are set
for var in ["BACKEND_HREF", "BROKER_HREF"]:
    try:
        os.environ[f"SIMWORKER_{var}"]
    except KeyError as e:
        logger.critical(f"Required ENVVAR 'SIMWORKER_{var}' is not set, exciting...")
        sys.exit(EXIT_ENVVAR_MISSING)


# Instantiate Celery-application
app = Celery(
    "worker",
    backend=os.environ["SIMWORKER_BACKEND_HREF"],
    broker=os.environ["SIMWORKER_BROKER_HREF"],
    include=["worker.tasks"],
)


if __name__ == "__main__":
    app.start()
