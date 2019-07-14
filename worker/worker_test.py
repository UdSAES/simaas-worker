#! /usr/bin/python3
# -*- coding: utf8 -*-

import os
import pytest
import pandas as pd

from .worker import timeseries_dict_to_pd_series


class TestPreProcessing(object):

    def test_dict_2_pd_series(self):
        ts_obj = dict(
            label='temperature',
            unit='K',
            timeseries=[
                [1542412800000, 274.6336669921875],
                [1542416400000, 274.4828796386719],
                [1542420000000, 274.01922607421875]
            ]
        )

        ts_pd_series = pd.Series(
            [274.6336669921875, 274.4828796386719, 274.01922607421875],
            index=[1542412800000, 1542416400000, 1542420000000],
            name='temperature'
        )

        s = timeseries_dict_to_pd_series(ts_obj)

        assert s.equals(ts_pd_series)


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
