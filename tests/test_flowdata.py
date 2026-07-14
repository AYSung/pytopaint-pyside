import anndata as ad
import numpy as np
import pandas as pd
import pytest
import yaml

from pytopaint.flowdata import (
    UPPER_PHYSICAL,
    _clean_marker_name,
    extract_case_number,
    get_axis_ticks,
    sort_channels,
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
    assert _clean_marker_name('CD41/CD61') == 'CD41/CD61'


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
        'UMAP1': [-1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 10],
        'Time': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
    })


@pytest.fixture
def adata_1() -> ad.AnnData:
    adata = ad.AnnData(np.array([[0, 0, 0], [0, 0, 0]]))
    adata.var_names = ['FSC-A', 'CD45', 'Time']
    adata.var['channel_type'] = ['scatter', 'fluoro', 'time']
    adata.uns['scaling_factor'] = 150
    adata.var['lower_bound'] = [0, LOWER_ASINH, 0]
    adata.var['upper_bound'] = [UPPER_PHYSICAL, UPPER_ASINH, 100]
    return adata


def test_get_axis_ticks(adata_1):
    axis_ticks = get_axis_ticks(adata_1, bins=256)

    assert axis_ticks['FSC-A'] == [
        (0, '0'),
        (50, None),
        (100, '1e5'),
        (150, None),
        (200, '2e5'),
    ]
    assert axis_ticks['CD45'] == [
        (11, None),
        (29, '0'),
        (47, None),
        (102, '1e3'),
        (167, '1e4'),
        (233, '1e5'),
    ]
    assert axis_ticks['Time'] == [
        (0, None),
        (64, None),
        (128, None),
        (192, None),
        (255, None),
    ]


def test_extract_case_number():
    assert extract_case_number('Z-26-1234 JOHN SMITH') == 'IP26-01234'
    assert extract_case_number('Z-24-12345 SMITH') == 'IP24-12345'
    assert extract_case_number('Z-24-1234 SMITH') == 'IP24-01234'
    assert extract_case_number('Z-24-1234 SMITH') == 'IP24-01234'
    assert extract_case_number('Y 24-1234 SMITH') == 'IP24-01234'
    assert extract_case_number('Y 24-1234 SMITH1') == 'IP24-01234'
    assert extract_case_number('Z-24-1234 JOHN-SMITH') == 'IP24-01234'
    assert extract_case_number('Y 1234 SMITH') == 'IPxx-01234'
