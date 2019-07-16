#! /usr/bin/python3
# -*- coding: utf8 -*-


import os
import sys
import json
import socket

from loguru import logger

from .worker import FILLNA
from .worker import timeseries_dict_to_pd_series
from .worker import prepare_bc_for_fmpy
from .worker import simulate_fmu2_cs


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
    level=os.environ['LOG_LEVEL'] if 'LOG_LEVEL' in os.environ else 'INFO',
    serialize=True
)


def main():

    pass
