#! /usr/bin/python3
# -*- coding: utf8 -*-

import os
import pytest


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
