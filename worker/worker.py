#! /usr/bin/python3
# -*- coding: utf8 -*-

import os
import sys
import json
import socket
from loguru import logger


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

    record['name'] = 'simaas_worker'
    record['time'] = record['time'].isoformat()
    record['pid'] = int(record['process'])
    record['msg'] = record['message']
    record['hostname'] = socket.gethostname()
    record['level'] = logger.level(record['level'])[0]
    if 'req_id' in record['extra']:
        record['req_id'] = record['extra']['req_id']

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


if __name__ == "__main__":
    sys.exit(main())
