import pytest
import re
import yaml

import flowkit
import pandas as pd


from pytopaint.io import (
    bin_df,
    clip_df,
    _get_channels,
    _get_compensation,
    LINEAR_PARAMETERS,
)


def load_panel_config() -> list[list[str]]:
    with open('pytopaint/resources/panels.yml') as stream:
        return yaml.safe_load(stream)


PANELS = load_panel_config()


def _get_biplot_dims(channels: list[str]) -> list[list[str, str]]:
    return [[x, y] for x, y in PANELS if x in channels and y in channels]


def _get_basic_dims(channels: list[str]) -> list[list[str, str]]:
    cd45_label = 'CD45 AF700' if 'CD45 AF700' in channels else 'CD45'
    return [['FSC-A', 'SSC-A'], ['SSC-A', cd45_label], ['FSC-A', 'FSC-H']]


def _get_ssc_dims(channels: list[str]) -> list[list[str, str]]:
    marker_channels = [
        channel for channel in channels if channel not in LINEAR_PARAMETERS
    ]
    cd_channels = sorted(
        [channel for channel in marker_channels if channel.startswith('CD')],
        key=lambda s: int(re.match(r'CD(\d+) ?', s).group(1)),
    )
    non_cd_channels = sorted(
        [channel for channel in marker_channels if not channel.startswith('CD')]
    )

    dims = [[channel, 'SSC-A'] for channel in cd_channels + non_cd_channels]
    return dims


def get_biplot_config(channels: list[str]) -> list[list[str, str]]:
    PANELS = [
        ['CD3', 'CD4'],
        ['CD4', 'CD8'],
        ['FSC-A', 'SSC-A'],
        ['CD7', 'CD3'],
    ]
    return [[x, y] for x, y in PANELS if (x in channels) and (y in channels)]


@pytest.fixture
def test_df_1():
    return pd.DataFrame({'FSC-A': [-1, 100], 'SSC-A': [-1, 100], 'CD45': [4, 10]})


def test_clip(test_df_1):
    pd.testing.assert_frame_equal(
        clip_df(test_df_1),
        pd.DataFrame({'FSC-A': [0, 100], 'SSC-A': [0, 100], 'CD45': [4, 8]}),
    )


def test_bin(test_df_1):
    binned_df = bin_df(clip_df(test_df_1), n_bins=256)
    pd.testing.assert_frame_equal(
        binned_df,
        pd.DataFrame({'FSC-A': [0, 0], 'SSC-A': [0, 0], 'CD45': [142, 255]}),
    )


def test_get_channels():
    test_df = pd.DataFrame(
        [
            ('FSC-A', ''),
            ('FSC-H', ''),
            ('SSC-A', ''),
            ('SSC-H', ''),
            ('fluor1', 'CD2'),
            ('fluor2', 'CD3'),
            ('fluor3', 'CD64'),
            ('Time', ''),
        ],
        columns=['pnn', 'pns'],
    )
    assert _get_channels(test_df) == [
        'FSC-A',
        'FSC-H',
        'SSC-A',
        'SSC-H',
        'CD2',
        'CD3',
        'CD64',
        'Time',
    ]


def test_get_compensation():
    metadata_1 = {'spill': 'spill matrix'}
    metadata_2 = {'spillover': 'spillover matrix'}
    metadata_3 = {'id': 'test'}

    assert _get_compensation(metadata_1) == 'spill matrix'
    assert _get_compensation(metadata_2) == 'spillover matrix'
    assert _get_compensation(metadata_3) is None
