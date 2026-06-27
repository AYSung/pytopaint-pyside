from pytopaint.widgets.immunophenotyper import get_ip_channels
import pytest

import pandas as pd


@pytest.fixture
def df() -> pd.DataFrame:
    return pd.DataFrame({
        'FSC-A': [0, 1, 1, 1, 4, 4, 5, 5, 5, 6],
        'FSC-H': [0, 2, 2, 2, 4, 4, 5, 6, 6, 5],
        'SSC-A': [0, 0, 0, 0, 3, 3, 4, 4, 4, 4],
        'SSC-H': [0, 0, 0, 0, 4, 4, 5, 5, 5, 6],
        'CD45': [5, 5, 5, 4, 4, 4, 3, 3, 3, 3],
        'CD19': [5, 5, 5, 5, 5, 3, 3, 2, 2, 2],
        'CD10': [3, 3, 2, 2, 2, 2, 1, 1, 1, 1],
        'Time': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        'color': [1, 1, 1, 1, 0, 0, 0, 2, 2, 2],
    })


def test_get_ip_channels(df: pd.DataFrame):
    assert get_ip_channels(['FSC-A', 'FSC-H', 'SSC-A', 'SSC-H', 'Time', 'color']) == [
        'FSC-A',
        'SSC-A',
    ]
    assert get_ip_channels(df.columns) == ['FSC-A', 'SSC-A', 'CD45', 'CD19', 'CD10']
    assert get_ip_channels([
        'FSC-A',
        'FSC-H',
        'SSC-A',
        'SSC-H',
        'CD45',
        'CD38',
        'UMAP1',
        'UMAP2',
        'Time',
    ]) == ['FSC-A', 'SSC-A', 'CD45', 'CD38']
