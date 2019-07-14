#! /usr/bin/python3
# -*- coding: utf8 -*-

import os

import pytest
import pandas as pd
import numpy as np

from .worker import FILLNA
from .worker import timeseries_dict_to_pd_series
from .worker import prepare_bc_for_fmpy


class TestPreProcessing(object):
    t2m_ts_obj = dict(
        label='temperature',
        unit='K',
        timeseries=[
            [1542412800000, 274.6336669921875],
            [1542416400000, 274.4828796386719],
            [1542420000000, 274.01922607421875]
        ]
    )

    t2m_pd_series = pd.Series(
        [274.6336669921875, 274.4828796386719, 274.01922607421875],
        index=[1542412800000, 1542416400000, 1542420000000],
        name='temperature'
    )

    aswdir_s_ts_obj = dict(
        label='directHorizontalIrradiance',
        unit='W/m.2',
        timeseries=[
            [1542412800000, 0.0],
            [1542420000000, 0.0]
        ]
    )

    aswdir_s_pd_series = pd.Series(
        [0.0, 0.0],
        index=[1542412800000, 1542420000000],
        name='directHorizontalIrradiance'
    )

    bc = np.array(
        [
            (0.0, 274.6336669921875, 0.0),
            (3600.0, 274.4828796386719, FILLNA),  # NaN replaced by constant value
            (7200.0, 274.01922607421875, 0.0)
        ],
        dtype=[
            ('time', np.double),
            ('temperature', np.double),
            ('directHorizontalIrradiance', np.double)
        ]
    )

    def test_dict_2_pd_series(self):
        s = timeseries_dict_to_pd_series(self.t2m_ts_obj)

        assert s.equals(self.t2m_pd_series)

    def test_bc_for_fmpy(self):
        signals = prepare_bc_for_fmpy(
            [self.t2m_pd_series, self.aswdir_s_pd_series],
            units=[self.t2m_ts_obj['unit'], self.aswdir_s_ts_obj['unit']]
        )


        assert np.array_equal(self.bc, signals) is True

class TestSimulateFMU2forCS(object):
    test_data_base_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '..', 'tests', 'data'
    )

    fmu_filepath = os.path.join(
        test_data_base_path,
        'c02f1f12-966d-4eab-9f21-dcf265ceac71',
        'model_instance.fmu'
    )

    def test_fmu_exists(self):
        assert os.path.isfile(self.fmu_filepath)

    @pytest.mark.skip
    def test_fmu_does_not_exist(self):
        pass

    @pytest.mark.skip
    def test_successful_simulation(self):
        pass
