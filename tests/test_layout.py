import pytest

from pytopaint.layout import (
    _to_grid_coordinates,
    LayoutConfig,
    get_best_layout,
    _extend_list,
    _import_layouts,
)


def test_grid_coordinates():
    assert _to_grid_coordinates(3, 4) == [
        (0, 0),
        (0, 1),
        (0, 2),
        (0, 3),
        (1, 0),
        (1, 1),
        (1, 2),
        (1, 3),
        (2, 0),
        (2, 1),
        (2, 2),
        (2, 3),
    ]
    assert _to_grid_coordinates(2, 6) == [
        (0, 0),
        (0, 1),
        (0, 2),
        (0, 3),
        (0, 4),
        (0, 5),
        (1, 0),
        (1, 1),
        (1, 2),
        (1, 3),
        (1, 4),
        (1, 5),
    ]


@pytest.fixture
def test_channels_1() -> list[str]:
    return [
        'FSC-A',
        'FSC-H',
        'SSC-A',
        'SSC-H',
        'CD5',
        'CD10',
        'CD19',
        'CD20',
        'CD22',
        'CD34',
        'CD38',
        'CD45',
        'Kappa',
        'Lambda',
        'Time',
    ]


@pytest.fixture
def test_channels_2() -> list[str]:
    return [
        'FSC-A',
        'FSC-H',
        'SSC-A',
        'SSC-H',
        'CD2',
        'CD3',
        'CD4',
        'CD5',
        'CD7',
        'CD8',
        'CD14',
        'CD56',
        'CD64',
        'CD45',
        'Time',
    ]


@pytest.fixture
def test_layout_1() -> list[tuple[str, str]]:
    return [
        [('CD5', 'CD19'), ('CD10', 'CD19'), ('CD10', 'CD20'), ('Lambda', 'Kappa')],
        [('CD20', 'CD38'), ('CD45', 'CD38'), ('CD34', 'CD38'), ('CD22', 'CD34')],
    ]


@pytest.fixture
def test_layout_2() -> list[tuple[str, str]]:
    return [
        [('CD5', 'CD19'), ('CD10', 'CD19'), ('CD10', 'CD20')],
        [('Lambda', 'Kappa'), ('CD20', 'CD38'), ('CD45', 'CD38')],
        [('CD34', 'CD38'), ('CD22', 'CD34'), ('CD30', 'SSC-A')],
    ]


@pytest.fixture
def test_layout_3() -> list[tuple[str, str]]:
    return [
        [
            ('CD7', 'CD3'),
            ('CD2', 'CD3'),
            ('CD4', 'CD8'),
            ('CD2', 'CD5'),
            ('CD3', 'CD5'),
            ('CD7', 'CD5'),
            ('CD8', 'CD5'),
        ],
        [
            ('CD56', 'CD45'),
            ('CD2', 'CD56'),
            ('CD4', 'CD14'),
            ('CD64', 'CD14'),
            ('CD64', 'CD45'),
            ('CD4', 'CD7'),
        ],
    ]


@pytest.fixture
def layout_1(test_layout_1) -> LayoutConfig:
    return LayoutConfig(test_layout_1)


@pytest.fixture
def layout_2(test_layout_3) -> LayoutConfig:
    return LayoutConfig(test_layout_3)


def test_layout_config(
    layout_1: LayoutConfig,
    layout_2: LayoutConfig,
    test_layout_1,
    test_layout_3,
    test_channels_1,
    test_channels_2,
):
    assert layout_1.layout == test_layout_1
    assert layout_1.rows == 2
    assert layout_1.cols == 4
    assert layout_1.channels == {
        'CD5',
        'CD19',
        'CD10',
        'CD20',
        'Lambda',
        'Kappa',
        'CD38',
        'CD45',
        'CD34',
        'CD22',
    }
    assert layout_1.flattened() == [
        ('CD5', 'CD19'),
        ('CD10', 'CD19'),
        ('CD10', 'CD20'),
        ('Lambda', 'Kappa'),
        ('CD20', 'CD38'),
        ('CD45', 'CD38'),
        ('CD34', 'CD38'),
        ('CD22', 'CD34'),
    ]
    assert layout_1.biplot_score(test_channels_1) == 1
    assert layout_1.biplot_score(test_channels_2) == 0
    assert layout_1.channel_score(test_channels_1) == 10 / 15
    assert layout_1.channel_score(test_channels_2) == 2 / 15
    assert layout_1.to_grid() == {
        (0, 0): ('CD5', 'CD19'),
        (0, 1): ('CD10', 'CD19'),
        (0, 2): ('CD10', 'CD20'),
        (0, 3): ('Lambda', 'Kappa'),
        (1, 0): ('CD20', 'CD38'),
        (1, 1): ('CD45', 'CD38'),
        (1, 2): ('CD34', 'CD38'),
        (1, 3): ('CD22', 'CD34'),
    }

    assert layout_2.layout == test_layout_3
    assert layout_2.rows == 2
    assert layout_2.cols == 7
    assert layout_2.channels == {
        'CD7',
        'CD3',
        'CD2',
        'CD4',
        'CD5',
        'CD8',
        'CD56',
        'CD45',
        'CD14',
        'CD64',
    }
    assert layout_2.flattened() == [
        ('CD7', 'CD3'),
        ('CD2', 'CD3'),
        ('CD4', 'CD8'),
        ('CD2', 'CD5'),
        ('CD3', 'CD5'),
        ('CD7', 'CD5'),
        ('CD8', 'CD5'),
        ('CD56', 'CD45'),
        ('CD2', 'CD56'),
        ('CD4', 'CD14'),
        ('CD64', 'CD14'),
        ('CD64', 'CD45'),
        ('CD4', 'CD7'),
        (None, None),
    ]
    assert layout_2.biplot_score(test_channels_1) == 0
    assert layout_2.biplot_score(test_channels_2) == 1
    assert layout_2.channel_score(test_channels_1) == 2 / 15
    assert layout_2.channel_score(test_channels_2) == 10 / 15
    assert layout_2.to_grid() == {
        (0, 0): ('CD7', 'CD3'),
        (0, 1): ('CD2', 'CD3'),
        (0, 2): ('CD4', 'CD8'),
        (0, 3): ('CD2', 'CD5'),
        (0, 4): ('CD3', 'CD5'),
        (0, 5): ('CD7', 'CD5'),
        (0, 6): ('CD8', 'CD5'),
        (1, 0): ('CD56', 'CD45'),
        (1, 1): ('CD2', 'CD56'),
        (1, 2): ('CD4', 'CD14'),
        (1, 3): ('CD64', 'CD14'),
        (1, 4): ('CD64', 'CD45'),
        (1, 5): ('CD4', 'CD7'),
        (1, 6): (None, None),
    }


def test_match_layout_to_grid(
    layout_1,
    test_channels_1,
    test_channels_2,
    layout_2,
):
    assert (
        get_best_layout(
            channels=test_channels_1,
            layouts=[layout_1, layout_2],
        )
        == layout_1
    )
    assert (
        get_best_layout(
            channels=test_channels_2,
            layouts=[layout_1, layout_2],
        )
        == layout_2
    )


def test_extend_list():
    assert _extend_list(
        [('FSC-A', 'SSC-A'), ('CD19', 'CD5'), ('CD20', 'CD10')], target_length=5
    ) == [
        ('FSC-A', 'SSC-A'),
        ('CD19', 'CD5'),
        ('CD20', 'CD10'),
        (None, None),
        (None, None),
    ]


def test_import_layout(layout_1):
    assert _import_layouts('tests.resources.layouts') == [layout_1]
