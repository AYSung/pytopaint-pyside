from pytopaint.widgets.immunophenotyper import (
    get_ip_channels,
    generate_report_template,
    _add_marker_smartlist,
    _join_list,
)
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


def test_generate_report_template():
    assert (
        generate_report_template(
            ip_channels=['FSC-A', 'SSC-A', 'CD5', 'CD10', 'CD19', 'CD20'],
            percent_events=0.213,
        )
        == 'Immunophenotypic analysis reveals a population of {cell lineage selection:40658} cells (21.3% of total events) with {light scatter strength:40657} forward light scatter, {light scatter strength:40657} orthogonal light scatter, and the following immunophenotype: CD5 ({+/-:40630}), CD10 ({+/-:40630}), CD19 ({+/-:40630}), and CD20 ({+/-:40630})'
    )
    assert (
        generate_report_template(
            ip_channels=[
                'FSC-A',
                'SSC-A',
                'CD5',
                'CD10',
                'CD19',
                'CD20',
                'Kappa',
                'Lambda',
            ],
            percent_events=0.0003,
        )
        == 'Immunophenotypic analysis reveals a population of {cell lineage selection:40658} cells (0.03% of total events) with {light scatter strength:40657} forward light scatter, {light scatter strength:40657} orthogonal light scatter, and the following immunophenotype: CD5 ({+/-:40630}), CD10 ({+/-:40630}), CD19 ({+/-:40630}), CD20 ({+/-:40630}), {surface/IC:46754} kappa light chain ({+/-:40630}), and {surface/IC:46754} lambda light chain ({+/-:40630})'
    )


def test_add_marker_smartlist():
    assert _add_marker_smartlist('CD5') == 'CD5 ({+/-:40630})'
    assert _add_marker_smartlist('CD10') == 'CD10 ({+/-:40630})'
    assert _add_marker_smartlist('TRBC1') == 'TRBC1 ({+/-:40630})'
    assert (
        _add_marker_smartlist('Kappa')
        == '{surface/IC:46754} kappa light chain ({+/-:40630})'
    )


def test_join_list():
    assert _join_list(['CD5', 'CD10', 'CD20']) == 'CD5, CD10, and CD20'
    assert _join_list(['CD5', 'CD10']) == 'CD5 and CD10'
    assert _join_list(['CD5']) == 'CD5'
    assert _join_list([]) == ''
