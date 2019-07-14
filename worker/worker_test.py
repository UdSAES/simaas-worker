#! /usr/bin/python3
# -*- coding: utf8 -*-

import os

import pytest
import pandas as pd
import numpy as np

from .worker import FILLNA
from .worker import timeseries_dict_to_pd_series
from .worker import prepare_bc_for_fmpy
from .worker import simulate_fmu2_cs


class DataContainer(object):
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

    aswdifd_s_ts_obj = dict(
        label='diffuseHorizontalIrradiance',
        unit='W/m.2',
        timeseries=[
            [1542412800000, 0.0],
            [1542416400000, 0.0],
            [1542420000000, 0.0]
        ]
    )

    aswdifd_s_pd_series = pd.Series(
        [0.0, 0.0, 0.0],
        index=[1542412800000, 1542416400000, 1542420000000],
        name='diffuseHorizontalIrradiance'
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


class TestPreProcessing(object):
    d = DataContainer()

    def test_dict_2_pd_series(self):
        s = timeseries_dict_to_pd_series(self.d.t2m_ts_obj)

        assert s.equals(self.d.t2m_pd_series)

    def test_bc_for_fmpy(self):
        signals = prepare_bc_for_fmpy(
            [self.d.t2m_pd_series, self.d.aswdir_s_pd_series],
            units=[self.d.t2m_ts_obj['unit'], self.d.aswdir_s_ts_obj['unit']]
        )


        assert np.array_equal(self.d.bc, signals) is True

class TestSimulateFMU2forCS(object):
    d = DataContainer()

    test_data_base_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '..', 'tests', 'data'
    )

    fmu_filepath = os.path.join(
        test_data_base_path,
        'c02f1f12-966d-4eab-9f21-dcf265ceac71',
        'model_instance.fmu'
    )

    options = dict(
        simulationParameters=dict(
            startTime=1542412800000,
            stopTime=1542420000000,
            outputInterval=3600
        ),
        inputTimeseries=[
            d.t2m_ts_obj,
            d.aswdir_s_ts_obj,
            d.aswdifd_s_ts_obj
        ]
    )

    def _pd_df_equal(self, a, b):
        try:
            pd.testing.assert_frame_equal(
                a,
                b,
                check_dtype=True,
                check_index_type='equiv',
                check_column_type='equiv',
                check_frame_type=True,
                check_less_precise=False,
                check_names=True,
                check_exact=False
            )
        except AssertionError:
            return False
        return True

    # Verify that FMU used for testing is available
    def test_fmu_exists(self):
        assert os.path.isfile(self.fmu_filepath)

    # Function MUST raise an error if the FMU does not exist
    @pytest.mark.skip
    def test_fmu_does_not_exist(self):
        pass

    # Actual simulation result MUST match expected result
    def test_successful_simulation(self):
        expected = pd.DataFrame(
            data={'powerDC': [0.0, 0.0, 0.0], 'totalEnergyDC': [0.0, 0.0, 0.0]},
            index=[1542412800000, 1542416400000, 1542420000000]
        )
        expected.set_index(pd.DatetimeIndex(expected.index*10**6), inplace=True)
        expected.index.name = 'time'

        df = simulate_fmu2_cs(self.fmu_filepath, self.options, req_id=None)

        assert self._pd_df_equal(df, expected) is True

    # Logs MUST match the agreed upon schema
    @pytest.mark.skip
    def test_log_format(self):
        pass
