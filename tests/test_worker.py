#! /usr/bin/python3
# -*- coding: utf8 -*-

"""Run unit tests for actual functionality."""

import os

import pytest
import pandas as pd
import numpy as np

from worker import timeseries_dict_to_pd_series
from worker import prepare_bc_for_fmpy
from worker import simulate_fmu2_cs

from tests import mwe
from tests import fmpy_issue89
from tests import pv_20181117_15kWp_saarbruecken


@pytest.mark.parametrize(
    "ctx", [
        mwe(),
        fmpy_issue89(),
        pv_20181117_15kWp_saarbruecken(),
    ]
)
class TestPreProcessing(object):
    def test_dict_2_pd_series(self, ctx):
        if 'timeseries_dict_to_pd_series' in ctx['expectations']:
            req_body = ctx['data']['mq_payload']['request']['body']
            input = req_body['inputTimeseries'][0]
            desired = ctx['expectations']['timeseries_dict_to_pd_series']['t2m']
            actual = timeseries_dict_to_pd_series(input)

            assert actual.equals(desired)
        else:
            pytest.skip('skipped because no expectation was specified')

    def test_bc_for_fmpy(self, ctx):
        if 'prepare_bc_for_fmpy' in ctx['expectations']:
            req_body = ctx['data']['mq_payload']['request']['body']
            desired = ctx['expectations']['prepare_bc_for_fmpy']
            actual = prepare_bc_for_fmpy(
                [
                    timeseries_dict_to_pd_series(req_body['inputTimeseries'][0]),
                    timeseries_dict_to_pd_series(req_body['inputTimeseries'][1]),
                    timeseries_dict_to_pd_series(req_body['inputTimeseries'][2]),
                ],
                units=[
                    req_body['inputTimeseries'][0]['unit'],
                    req_body['inputTimeseries'][1]['unit'],
                    req_body['inputTimeseries'][2]['unit']
                ]
            )

            assert np.array_equal(actual, desired) is True
        else:
            pytest.skip('skipped because no expectation was specified')

@pytest.mark.parametrize(
    "ctx", [
        mwe(),
        fmpy_issue89(),
        pv_20181117_15kWp_saarbruecken(),
    ]
)
class TestSimulateFMU2forCS(object):

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
    def test_fmu_exists(self, ctx, fmu_filepath):
        assert os.path.isfile(fmu_filepath)

    # Function MUST raise an error if the FMU does not exist
    @pytest.mark.skip
    def test_fmu_does_not_exist(self, ctx, fmu_filepath):
        pass

    # Actual simulation result MUST match expected result
    def test_successful_simulation(self, ctx, fmu_filepath):
        if 'simulate_fmu2_cs' in ctx['expectations']:
            desired = ctx['expectations']['simulate_fmu2_cs']
            options = ctx['data']['mq_payload']['request']['body']
            req_id = ctx['data']['mq_payload']['request']['id']

            actual = simulate_fmu2_cs(fmu_filepath, options, req_id)

            assert self._pd_df_equal(actual, desired) is True
        else:
            pytest.skip('skipped because no expectation was specified')

    # Logs MUST match the agreed upon schema
    @pytest.mark.skip
    def test_log_format(self, ctx):
        pass
    #     simulate_fmu2_cs(fmu_filepath, {})
    #     # https://docs.pytest.org/en/latest/
    #     # -- logging.html
    #     # -- capture.html#accessing-captured-output-from-a-test-function
    #     captured = capsys.readouterr()
    #
    #     for log in captured.out.split('\n'):
    #         if log != '':
    #             log_obj = json.loads(log)
    #             print(log_obj['msg'])
