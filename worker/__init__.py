#! /usr/bin/python3
# -*- coding: utf8 -*-


import os
import sys
import json
import socket

from loguru import logger

from .worker import FILLNA  # noqa
from .worker import timeseries_dict_to_pd_series  # noqa
from .worker import prepare_bc_for_fmpy  # noqa
from .worker import simulate_fmu2_cs  # noqa


# Configure logging
def sink_JSON_stdout_designetz(message):
    record = message.record
    info_not_wanted = [
        'elapsed',
        'exception',
        'extra',
        'file',
        'function',
        'line',
        'message',
        'module',
        'process',
        'thread',
    ]
    info_wanted = [
        'req_id',
        'code'
    ]

    record['name'] = 'simaas_worker'
    record['time'] = record['time'].isoformat()
    record['pid'] = int(record['process'])
    record['msg'] = record['message']
    record['hostname'] = socket.gethostname()
    record['level'] = logger.level(record['level'])[0]
    for field in info_wanted:
        if field in record['extra']:
            record[field] = record['extra'][field]

    for item in info_not_wanted:
        record.pop(item)

    print(json.dumps(record), file=sys.stdout)


logger.remove()
log_level = os.getenv("SIMWORKER_LOG_LEVEL", "INFO")
if os.getenv("SIMWORKER_LOG_STRUCTURED", "true") is "true":
    logger.configure(
        levels=[
            dict(name='TRACE', no=10),
            dict(name='DEBUG', no=20),
            dict(name='INFO', no=30),
            dict(name='WARNING', no=40),
            dict(name='ERROR', no=50),
            dict(name='FATAL', no=60),
            dict(name='CRITICAL', no=60)
        ]
    )

    logger.add(
        sink_JSON_stdout_designetz,
        level=log_level,
        serialize=True
    )
else:
    logger.add(sys.stdout, level=log_level, diagnose=True, backtrace=False)




# Run module
@logger.catch
def main():

    test_data_base_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '..', 'tests', 'data'
    )

    model_instance_id = 'c02f1f12-966d-4eab-9f21-dcf265ceac71'

    fmu_filepath = os.path.join(
        test_data_base_path,
        model_instance_id,
        'model_instance.fmu'
    )

    req_body_json_file = os.path.join(
        test_data_base_path, model_instance_id,
        '20181117_req_body_saarbruecken.json'
    )
    with open(req_body_json_file) as fp:
        req_body = json.load(fp)

    result = simulate_fmu2_cs(fmu_filepath, req_body, req_id=None)

    print(result)
