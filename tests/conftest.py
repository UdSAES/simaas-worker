#! /usr/bin/python3
# -*- coding: utf8 -*-

"""Provide test fixtures for unit tests.

Also, modify PATH to resolve references properly; see
https://docs.python-guide.org/writing/structure/#test-suite
for an explanation.
"""

import json
import os
import sys

import numpy as np
import pandas as pd
import pendulum
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import worker  # noqa -- import has to happen _after_ modifying PATH

test_data_base_path = os.path.normpath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "tests", "data")
)


def mwe():
    """Provide minimal data set for testing the simulation of a PV plant."""

    sim_result_df = pd.DataFrame(
        data={"powerDC": [0.0, 0.0, 0.0], "totalEnergyDC": [0.0, 0.0, 0.0]},
        index=[1542412800000, 1542416400000, 1542420000000],
    )
    sim_result_df.set_index(
        pd.DatetimeIndex(sim_result_df.index * 10 ** 6).tz_localize("utc"), inplace=True
    )
    sim_result_df.index.name = "time"

    context = dict(
        data=dict(
            mq_payload=dict(
                request=dict(
                    id="cd376d13-d0ba-4979-bd41-485d5121ae93",
                    body={
                        "modelInstanceID": "c02f1f12-966d-4eab-9f21-dcf265ceac71",
                        "simulationParameters": {
                            "startTime": 1542412800000,
                            "stopTime": 1542420000000,
                            "outputInterval": 3600,
                            "inputTimeIsRelative": "false",
                        },
                        "inputTimeseries": [
                            {
                                "label": "temperature",
                                "unit": "K",
                                "timeseries": [
                                    {
                                        "timestamp": 1542412800000,
                                        "value": 274.6336669921875,
                                    },
                                    {
                                        "timestamp": 1542416400000,
                                        "value": 274.4828796386719,
                                    },
                                    {
                                        "timestamp": 1542420000000,
                                        "value": 274.01922607421875,
                                    },
                                ],
                            },
                            {
                                "label": "directHorizontalIrradiance",
                                "unit": "W/m.2",
                                "timeseries": [
                                    {"timestamp": 1542412800000, "value": 0.0},
                                    {"timestamp": 1542420000000, "value": 0.0},
                                ],
                            },
                            {
                                "label": "diffuseHorizontalIrradiance",
                                "unit": "W/m.2",
                                "timeseries": [
                                    {"timestamp": 1542412800000, "value": 0.0},
                                    {"timestamp": 1542416400000, "value": 0.0},
                                    {"timestamp": 1542420000000, "value": 0.0},
                                ],
                            },
                        ],
                    },
                )
            )
        ),
        expectations=dict(
            timeseries_dict_to_pd_series=dict(
                t2m=pd.Series(
                    [274.6336669921875, 274.4828796386719, 274.01922607421875],
                    index=[1542412800000, 1542416400000, 1542420000000],
                    name="temperature",
                ),
                aswdir_s=pd.Series(
                    [0.0, 0.0],
                    index=[1542412800000, 1542420000000],
                    name="directHorizontalIrradiance",
                ),
                aswdifd_s=pd.Series(
                    [0.0, 0.0, 0.0],
                    index=[1542412800000, 1542416400000, 1542420000000],
                    name="diffuseHorizontalIrradiance",
                ),
            ),
            prepare_bc_for_fmpy=np.array(
                [
                    (0.0, 274.6336669921875, 0.0, 0.0),
                    (3600.0, 274.4828796386719, worker.FILLNA, 0.0),
                    (7200.0, 274.01922607421875, 0.0, 0.0),
                ],
                dtype=[
                    ("time", np.double),
                    ("temperature", np.double),
                    ("directHorizontalIrradiance", np.double),
                    ("diffuseHorizontalIrradiance", np.double),
                ],
            ),
            simulate_fmu2_cs=sim_result_df,
        ),
    )

    return context


def fmpy_issue89():
    """Ensure that issue #89 in FMPy is resolved.

    When reading input data from a .csv-file in FMPy, the values are shifted in time by one output
    interval. This was reported in https://github.com/CATIA-Systems/FMPy/issues/89 -- the minimal
    working example described there is implemented in this test.
    """

    model_instance_id = "fmpy_issue89"
    # input_csv = os.path.join(
    #     test_data_base_path, model_instance_id,
    #     'MinimalWorkingExampleInputShifting_in.csv'
    # )
    # input_ndarray = np.genfromtxt(
    #     input_csv=os.path.join(input_csv, delimiter=',', names=True, deletechars='')
    # )

    sim_result_df = pd.DataFrame(
        data={"y1": [float(x) for x in list(range(0, 40, 5))]},
        index=pd.Index([x / 10 for x in list(range(0, 40, 5))], dtype="float"),
    )
    sim_result_df.index.name = "time"

    context = dict(
        data=dict(
            mq_payload=dict(
                request=dict(
                    id=model_instance_id,
                    body={
                        "modelInstanceID": model_instance_id,
                        "simulationParameters": {
                            "startTime": 0,
                            "stopTime": 3.5,
                            "outputInterval": 0.5,
                            "inputTimeIsRelative": "true",
                        },
                        "inputTimeseries": [
                            {
                                "label": "u1",
                                "unit": "1",
                                "timeseries": [
                                    {"timestamp": 0, "value": 0},
                                    {"timestamp": 1, "value": 10},
                                    {"timestamp": 2, "value": 20},
                                    {"timestamp": 3, "value": 30},
                                    {"timestamp": 4, "value": 40},
                                    {"timestamp": 5, "value": 50},
                                    {"timestamp": 6, "value": 60},
                                ],
                            }
                        ],
                    },
                )
            )
        ),
        expectations=dict(simulate_fmu2_cs=sim_result_df),
    )

    return context


def pv_20181117_15kWp_saarbruecken():
    """Provide data set for 15kWp PV plant on 20181117 at Saarland Uni."""
    model_instance_id = "c02f1f12-966d-4eab-9f21-dcf265ceac71"
    req_body_json_file = os.path.join(
        test_data_base_path, model_instance_id, "20181117_req_body_saarbruecken.json"
    )
    with open(req_body_json_file) as fp:
        req_body = json.load(fp)

    # Load results from .csv-file and index by datetime; values only at n*output_interval
    sim_result_csv = os.path.join(
        test_data_base_path,
        model_instance_id,
        "20181117_dymola2019_result_powerDC_totalEnergyDC_900s.csv",
    )
    sim_result_df = pd.read_csv(
        sim_result_csv,
        sep=",",
        header=0,
        names=["time", "powerDC", "totalEnergyDC"],
        decimal=".",
    )
    sim_result_df["time"] = sim_result_df["time"].apply(
        lambda x: req_body["simulationParameters"]["startTime"] + x * 1000
    )  # transform relative time in seconds to epoch in milliseconds
    sim_result_df = sim_result_df[
        sim_result_df["time"] % req_body["simulationParameters"]["outputInterval"] == 0
    ]  # drop values at intermediate points in time (i.e. not on dense output grid)
    sim_result_df.drop_duplicates("time", inplace=True)  # drop duplicates on index
    sim_result_df.set_index(
        pd.DatetimeIndex(sim_result_df["time"] * 10 ** 6).tz_localize("utc"),
        inplace=True,
    )
    del sim_result_df["time"]

    start_time = req_body["simulationParameters"]["startTime"]
    stop_time = req_body["simulationParameters"]["stopTime"]
    sim_result_df = sim_result_df[
        pendulum.from_timestamp(start_time / 1000)
        .to_datetime_string() : pendulum.from_timestamp(stop_time / 1000)
        .to_datetime_string()
    ]

    # Populate context-object
    context = dict(
        data=dict(
            mq_payload=dict(
                request=dict(id="3dcf3a45-36b7-4c2a-b1f0-473721fbec95", body=req_body)
            )
        ),
        expectations=dict(simulate_fmu2_cs=sim_result_df),
    )

    return context


@pytest.fixture
def fmu_filepath(ctx):
    fmu_filepath = os.path.join(
        test_data_base_path,
        ctx["data"]["mq_payload"]["request"]["body"]["modelInstanceID"],
        "model_instance.fmu",
    )

    return fmu_filepath
