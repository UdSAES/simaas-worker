#! /usr/bin/python3
# -*- coding: utf8 -*-

"""Provide test fixtures for unit tests."""

import os

import pytest
import numpy as np
import pandas as pd

from .worker import FILLNA


def mwe():
    """Provide minimal data set for testing the simulation a PV plant."""

    df_successful_sim = pd.DataFrame(
        data={'powerDC': [0.0, 0.0, 0.0], 'totalEnergyDC': [0.0, 0.0, 0.0]},
        index=[1542412800000, 1542416400000, 1542420000000]
    )
    df_successful_sim.set_index(pd.DatetimeIndex(df_successful_sim.index*10**6), inplace=True)
    df_successful_sim.index.name = 'time'

    context = dict(
        data=dict(
            mq_payload=dict(
                request=dict(
                    id='cd376d13-d0ba-4979-bd41-485d5121ae93',
                    body={
                      'modelInstanceID': 'c02f1f12-966d-4eab-9f21-dcf265ceac71',
                      'simulationParameters': {
                        'startTime': 1542412800000,
                        'stopTime': 1542420000000,
                        'outputInterval': 3600
                      },
                      'inputTimeseries': [{
                          'label': 'temperature',
                          'unit': 'K',
                          'timeseries': [
                            {'timestamp': 1542412800000, 'value': 274.6336669921875},
                            {'timestamp': 1542416400000, 'value': 274.4828796386719},
                            {'timestamp': 1542420000000, 'value': 274.01922607421875}
                          ]
                        },
                        {
                          'label': 'directHorizontalIrradiance',
                          'unit': 'W/m.2',
                          'timeseries': [
                            {'timestamp': 1542412800000, 'value': 0.0},
                            {'timestamp': 1542420000000, 'value': 0.0}
                          ]
                        },
                        {
                          'label': 'diffuseHorizontalIrradiance',
                          'unit': 'W/m.2',
                          'timeseries': [
                            {'timestamp': 1542412800000, 'value': 0.0},
                            {'timestamp': 1542416400000, 'value': 0.0},
                            {'timestamp': 1542420000000, 'value': 0.0}
                          ]
                        }
                      ]
                    }
                )
            )
        ),
        expectations=dict(
            timeseries_dict_to_pd_series=dict(
                t2m=pd.Series(
                    [274.6336669921875, 274.4828796386719, 274.01922607421875],
                    index=[1542412800000, 1542416400000, 1542420000000],
                    name='temperature'
                ),
                aswdir_s=pd.Series(
                    [0.0, 0.0],
                    index=[1542412800000, 1542420000000],
                    name='directHorizontalIrradiance'
                ),
                aswdifd_s=pd.Series(
                    [0.0, 0.0, 0.0],
                    index=[1542412800000, 1542416400000, 1542420000000],
                    name='diffuseHorizontalIrradiance'
                )
            ),
            prepare_bc_for_fmpy=np.array(
                [
                    (0.0, 274.6336669921875, 0.0, 0.0),
                    (3600.0, 274.4828796386719, FILLNA, 0.0),  # NaN replaced by constant value
                    (7200.0, 274.01922607421875, 0.0, 0.0)
                ],
                dtype=[
                    ('time', np.double),
                    ('temperature', np.double),
                    ('directHorizontalIrradiance', np.double),
                    ('diffuseHorizontalIrradiance', np.double)
                ]
            ),
            simulate_fmu2_cs=df_successful_sim
        )
    )

    return context


@pytest.fixture(scope='session')
def ctx():
    """Provide context for tests depending on ENVVAR `TEST_DATA`."""

    choice = os.environ['TEST_DATA'] if 'TEST_DATA' in os.environ else 'mwe'

    return {
        'mwe': mwe()
    }[choice]


@pytest.fixture
def fmu_filepath(ctx):
    test_data_base_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '..', 'tests', 'data'
    )
    fmu_filepath = os.path.join(
        test_data_base_path,
        ctx['data']['mq_payload']['request']['body']['modelInstanceID'],
        'model_instance.fmu'
    )

    return fmu_filepath
