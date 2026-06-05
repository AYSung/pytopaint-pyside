import pytest
import yaml

import pandas as pd


from pytopaint.flowdata import (
    bin_df,
    sort_channels,
    _clean_marker_name,
    _get_channels,
    _get_compensation,
    UPPER_PHYSICAL,
    lower_clip_limit,
    upper_clip_limit,
    clip_series,
    bin_series,
    get_axis_ticks,
    extract_case_info,
)

LOWER_ASINH = -1
UPPER_ASINH = 8


def test_clean_marker_name():
    assert _clean_marker_name('KAPPA') == 'Kappa'
    assert _clean_marker_name('m Kappa') == 'Kappa'
    assert _clean_marker_name('mKAPPA') == 'Kappa'
    assert _clean_marker_name('LAMBDA') == 'Lambda'
    assert _clean_marker_name('m Lambda') == 'Lambda'
    assert _clean_marker_name('mLAMBDA') == 'Lambda'
    assert _clean_marker_name('TDT') == 'TdT'
    assert _clean_marker_name('TdT') == 'TdT'
    assert _clean_marker_name('mpo') == 'MPO'

    assert _clean_marker_name('CD45 AF700') == 'CD45'
    assert _clean_marker_name('CD45') == 'CD45'
    assert _clean_marker_name('CD45 RA') == 'CD45 RA'
    assert _clean_marker_name('CD45 BV480') == 'CD45'
    assert _clean_marker_name('CD5 BV480') == 'CD5'
    assert _clean_marker_name('CD11b') == 'CD11b'


def load_panel_config() -> list[list[str]]:
    with open('pytopaint/resources/panels.yml') as stream:
        return yaml.safe_load(stream)


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
    return pd.DataFrame({
        'FSC-A': [-1, 100],
        'SSC-A': [-1, 100],
        'CD45': [4, 10],
        'Time': [0, 100],
    })


def test_get_channels():
    test_df = pd.DataFrame(
        [
            ('FSC-A', ''),
            ('FSC-H', ''),
            ('SSC-A', ''),
            ('SSC-H', ''),
            ('fluor1', 'CD2'),
            ('fluor2', 'CD11b'),
            ('fluor3', 'HLA-DR'),
            ('fluor4', 'CD45 AF700'),
            ('fluor5', 'mKAPPA'),
            ('fluor6', 'mLAMBDA'),
            ('fluor7', ''),
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
        'CD11b',
        'HLA-DR',
        'CD45',
        'Kappa',
        'Lambda',
        'fluor7',
        'Time',
    ]


def test_get_compensation():
    metadata_1 = {'spill': 'spill matrix'}
    metadata_2 = {'spillover': 'spillover matrix'}
    metadata_3 = {'id': 'test'}

    assert _get_compensation(metadata_1) == 'spill matrix'
    assert _get_compensation(metadata_2) == 'spillover matrix'
    assert _get_compensation(metadata_3) is None


def test_sort_channels():
    test_channels = [
        'CD12',
        'CD45',
        'CD32',
        'CD123',
        'FSC-A',
        'FSC-H',
        'Time',
        'Lambda',
        'Kappa',
        'HLA-DR',
        'SSC-H',
        'SSC-A',
    ]

    assert sort_channels(test_channels) == [
        'FSC-A',
        'FSC-H',
        'SSC-A',
        'SSC-H',
        'CD12',
        'CD32',
        'CD45',
        'CD123',
        'HLA-DR',
        'Kappa',
        'Lambda',
        'Time',
    ]


@pytest.fixture
def df_1() -> pd.DataFrame:
    linear_param_values = [
        1e6,
        1e4,
        1e4,
        2e5,
        2e5,
        2e5,
        1e6,
        1e5,
        1e5,
        1e7,
        1e4,
        1e5,
        2e5,
        2e3,
        2e4,
        2e6,
        2e5,
        3e5,
        4e5,
        5e5,
    ]
    return pd.DataFrame({
        'FSC-A': linear_param_values,
        'FSC-H': linear_param_values,
        'SSC-A': linear_param_values,
        'SSC-H': linear_param_values,
        'CD5': [-4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 4, 3, 4, 5, 6, 7, 5, 5, 6, 5],
        'CD10': [0, 1, 2, 3, 4, 5, 6, 4, 5, 3, 6, 4, 5, 3, 2, 2, 4, 3, 14, 15],
        'Time': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
    })


def test_lower_clip_limits(df_1):
    assert lower_clip_limit(df_1['FSC-A']) == 0
    assert lower_clip_limit(df_1['FSC-H']) == 0
    assert lower_clip_limit(df_1['SSC-A']) == 0
    assert lower_clip_limit(df_1['SSC-H']) == 0
    assert lower_clip_limit(df_1['Time']) == 0
    assert lower_clip_limit(df_1['CD5']) < LOWER_ASINH
    assert lower_clip_limit(df_1['CD10']) == LOWER_ASINH


def test_upper_clip_limits(df_1):
    assert upper_clip_limit(df_1['FSC-A']) == UPPER_PHYSICAL
    assert upper_clip_limit(df_1['FSC-H']) == UPPER_PHYSICAL
    assert upper_clip_limit(df_1['SSC-A']) == UPPER_PHYSICAL
    assert upper_clip_limit(df_1['SSC-H']) == UPPER_PHYSICAL
    assert upper_clip_limit(df_1['Time']) == df_1['Time'].max()
    assert upper_clip_limit(df_1['CD5']) == UPPER_ASINH
    assert upper_clip_limit(df_1['CD10']) > UPPER_ASINH


def test_clip_series(test_df_1):
    clip_limits = {
        'FSC-A': (0, UPPER_PHYSICAL),
        'SSC-A': (0, UPPER_PHYSICAL),
        'CD45': (LOWER_ASINH, UPPER_ASINH),
        'Time': (0, 100),
    }

    pd.testing.assert_series_equal(
        clip_series(test_df_1['FSC-A'], clip_limits=clip_limits),
        pd.Series([0, 100], name='FSC-A'),
    )
    pd.testing.assert_series_equal(
        clip_series(test_df_1['SSC-A'], clip_limits=clip_limits),
        pd.Series([0, 100], name='SSC-A'),
    )
    pd.testing.assert_series_equal(
        clip_series(test_df_1['CD45'], clip_limits=clip_limits),
        pd.Series([4, 8], name='CD45'),
    )
    pd.testing.assert_series_equal(
        clip_series(test_df_1['Time'], clip_limits=clip_limits),
        pd.Series([0, 100], name='Time'),
    )


def test_bin_series(test_df_1):
    clip_limits = {
        'FSC-A': (0, UPPER_PHYSICAL),
        'SSC-A': (0, UPPER_PHYSICAL),
        'CD45': (LOWER_ASINH, UPPER_ASINH),
        'Time': (0, 100),
    }

    pd.testing.assert_series_equal(
        bin_series(
            clip_series(test_df_1['FSC-A'], clip_limits=clip_limits),
            n_bins=256,
            clip_limits=clip_limits,
        ),
        pd.Series([0, 0], name='FSC-A'),
    )
    pd.testing.assert_series_equal(
        bin_series(
            clip_series(test_df_1['SSC-A'], clip_limits=clip_limits),
            n_bins=256,
            clip_limits=clip_limits,
        ),
        pd.Series([0, 0], name='SSC-A'),
    )
    pd.testing.assert_series_equal(
        bin_series(
            clip_series(test_df_1['CD45'], clip_limits=clip_limits),
            n_bins=256,
            clip_limits=clip_limits,
        ),
        pd.Series([142, 255], name='CD45'),
    )
    pd.testing.assert_series_equal(
        bin_series(
            clip_series(test_df_1['Time'], clip_limits=clip_limits),
            n_bins=256,
            clip_limits=clip_limits,
        ),
        pd.Series([0, 255], name='Time'),
    )


def test_bin(test_df_1):
    clip_limits = {
        'FSC-A': (0, UPPER_PHYSICAL),
        'SSC-A': (0, UPPER_PHYSICAL),
        'CD45': (LOWER_ASINH, UPPER_ASINH),
        'Time': (0, 100),
    }
    binned_df = bin_df(test_df_1, n_bins=256, clip_limits=clip_limits)
    pd.testing.assert_frame_equal(
        binned_df,
        pd.DataFrame({
            'FSC-A': [0, 0],
            'SSC-A': [0, 0],
            'CD45': [142, 255],
            'Time': [0, 255],
        }),
    )


def test_get_axis_ticks():
    clip_limits = {
        'FSC-A': (0, UPPER_PHYSICAL),
        'CD45': (LOWER_ASINH, UPPER_ASINH),
        'Time': (0, 100),
    }
    assert get_axis_ticks(
        'FSC-A',
        n_bins=256,
        scaling_factor=150,
        clip_limits=clip_limits,
    ) == [(0, '0'), (50, None), (100, '1e5'), (150, None), (200, '2e5'), (250, None)]
    assert get_axis_ticks(
        'CD45',
        n_bins=256,
        scaling_factor=150,
        clip_limits=clip_limits,
    ) == [(10, None), (28, '0'), (46, None), (102, '1e3'), (167, '1e4'), (233, '1e5')]
    assert get_axis_ticks(
        'Time',
        n_bins=256,
        scaling_factor=150,
        clip_limits=clip_limits,
    ) == [(0, None), (64, None), (128, None), (192, None), (256, None)]


def test_extract_case_info():
    assert extract_case_info('normal_02_B') == 'normal_02_B'
    assert extract_case_info('CLL_01_B') == 'CLL_01_B'
    assert extract_case_info('Z-26-1234 JOHN SMITH_B CELL_001') == 'IP26-01234 B CELL'
    assert extract_case_info('Z-24-12345 SMITH_T CELL_002') == 'IP24-12345 T CELL'
    assert (
        extract_case_info('Z-24-1234 SMITH_CAR-T 19 TUBE 3_002')
        == 'IP24-01234 CAR-T 19 TUBE 3'
    )
    assert (
        extract_case_info('Z-24-1234 SMITH_1_BLL-REFLEX MRD_002')
        == 'IP24-01234 BLL-REFLEX MRD'
    )
    assert (
        extract_case_info('Y 24-1234 SMITH_1_BLL-REFLEX MRD_002')
        == 'IP24-01234 BLL-REFLEX MRD'
    )
