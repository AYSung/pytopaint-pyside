import pytest
from pytopaint.layout import (
    LayoutConfig,
    get_best_layout_match,
    _import_layouts,
    to_grid,
    replace_unused_channels,
)


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
            None,
            ('CD56', 'CD45'),
            ('CD2', 'CD56'),
            ('CD4', 'CD14'),
            ('CD64', 'CD14'),
            ('CD64', 'CD45'),
            ('CD4', 'CD7'),
        ],
    ]


@pytest.fixture
def test_layout_3() -> list[tuple[str, str]]:
    return [
        [('CD5', 'CD19'), ('CD10', 'CD19'), ('CD10', 'CD20')],
        [('Lambda', 'Kappa'), ('CD20', 'CD38'), ('CD45', 'CD38')],
        [('CD34', 'CD38'), ('CD22', 'CD34'), ('CD30', 'SSC-A')],
    ]


def test_to_grid(test_layout_1, test_layout_2, test_layout_3):
    assert to_grid(test_layout_1) == {
        (0, 0): ('CD5', 'CD19'),
        (0, 1): ('CD10', 'CD19'),
        (0, 2): ('CD10', 'CD20'),
        (0, 3): ('Lambda', 'Kappa'),
        (1, 0): ('CD20', 'CD38'),
        (1, 1): ('CD45', 'CD38'),
        (1, 2): ('CD34', 'CD38'),
        (1, 3): ('CD22', 'CD34'),
    }

    assert to_grid(test_layout_2) == {
        (0, 0): ('CD7', 'CD3'),
        (0, 1): ('CD2', 'CD3'),
        (0, 2): ('CD4', 'CD8'),
        (0, 3): ('CD2', 'CD5'),
        (0, 4): ('CD3', 'CD5'),
        (0, 5): ('CD7', 'CD5'),
        (0, 6): ('CD8', 'CD5'),
        (1, 1): ('CD56', 'CD45'),
        (1, 2): ('CD2', 'CD56'),
        (1, 3): ('CD4', 'CD14'),
        (1, 4): ('CD64', 'CD14'),
        (1, 5): ('CD64', 'CD45'),
        (1, 6): ('CD4', 'CD7'),
    }
    assert to_grid(test_layout_3) == {
        (0, 0): ('CD5', 'CD19'),
        (0, 1): ('CD10', 'CD19'),
        (0, 2): ('CD10', 'CD20'),
        (1, 0): ('Lambda', 'Kappa'),
        (1, 1): ('CD20', 'CD38'),
        (1, 2): ('CD45', 'CD38'),
        (2, 0): ('CD34', 'CD38'),
        (2, 1): ('CD22', 'CD34'),
        (2, 2): ('CD30', 'SSC-A'),
    }


@pytest.fixture
def layout_1(test_layout_1) -> LayoutConfig:
    return LayoutConfig(to_grid(test_layout_1))


@pytest.fixture
def layout_2(test_layout_2) -> LayoutConfig:
    return LayoutConfig(to_grid(test_layout_2))


def test_layout_config(
    layout_1: LayoutConfig,
    layout_2: LayoutConfig,
    test_layout_1,
    test_layout_2,
    test_channels_1,
    test_channels_2,
):
    assert layout_1.grid == to_grid(test_layout_1)
    assert layout_1.rows == 2
    assert layout_1.columns(row=0) == 4
    assert layout_1.columns(row=1) == 4
    assert layout_1.channels == [
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
    ]
    assert layout_1.biplot_score(test_channels_1) == 1
    assert layout_1.biplot_score(test_channels_2) == 0
    assert layout_1.channel_score(test_channels_1) == 10 / 15
    assert layout_1.channel_score(test_channels_2) == 2 / 15

    assert layout_2.grid == to_grid(test_layout_2)
    assert layout_2.rows == 2
    assert layout_2.columns(0) == 7
    assert layout_2.columns(1) == 7
    assert layout_2.channels == [
        'CD2',
        'CD3',
        'CD4',
        'CD5',
        'CD7',
        'CD8',
        'CD14',
        'CD45',
        'CD56',
        'CD64',
    ]
    assert layout_2.biplot_score(test_channels_1) == 0
    assert layout_2.biplot_score(test_channels_2) == 1
    assert layout_2.channel_score(test_channels_1) == 2 / 15
    assert layout_2.channel_score(test_channels_2) == 10 / 15


def test_match_layout_to_grid(
    layout_1,
    layout_2,
    test_channels_1,
    test_channels_2,
):
    assert (
        get_best_layout_match(
            channels=test_channels_1,
            layouts=[layout_1, layout_2],
        )
        == layout_1
    )
    assert (
        get_best_layout_match(
            channels=test_channels_2,
            layouts=[layout_1, layout_2],
        )
        == layout_2
    )


def test_import_layout(layout_1):
    assert _import_layouts('tests.resources.layouts') == [layout_1]


def test_replace_channels(layout_1, layout_2):
    assert replace_unused_channels(
        layout_1,
        [
            'FSC-A',
            'FSC-H',
            'SSC-A',
            'SSC-H',
            'CD5',
            'CD19',
            'CD10',
            'CD20',
            'Lambda',
            'Kappa',
            'CD38',
            'CD45',
            'CD30',
            'CD22',
            'Time',
        ],
    ) == LayoutConfig({
        (0, 0): ('CD5', 'CD19'),
        (0, 1): ('CD10', 'CD19'),
        (0, 2): ('CD10', 'CD20'),
        (0, 3): ('Lambda', 'Kappa'),
        (1, 0): ('CD20', 'CD38'),
        (1, 1): ('CD45', 'CD38'),
        (1, 2): ('CD30', 'CD38'),
        (1, 3): ('CD22', 'CD30'),
    })

    assert replace_unused_channels(
        layout_1,
        [
            'CD5',
            'CD19',
            'CD10',
            'CD20',
            'Lambda',
            'Kappa',
            'CD38',
            'CD45',
            'CD30',
            'CD22',
        ],
    ) == LayoutConfig({
        (0, 0): ('CD5', 'CD19'),
        (0, 1): ('CD10', 'CD19'),
        (0, 2): ('CD10', 'CD20'),
        (0, 3): ('Lambda', 'Kappa'),
        (1, 0): ('CD20', 'CD38'),
        (1, 1): ('CD45', 'CD38'),
        (1, 2): ('CD30', 'CD38'),
        (1, 3): ('CD22', 'CD30'),
    })

    assert replace_unused_channels(
        layout_2,
        [
            'CD2',
            'CD3',
            'CD4',
            'CD5',
            'CD7',
            'CD8',
            'CD14',
            'CD57',
            'CD64',
            'CD45',
        ],
    ) == LayoutConfig({
        (0, 0): ('CD7', 'CD3'),
        (0, 1): ('CD2', 'CD3'),
        (0, 2): ('CD4', 'CD8'),
        (0, 3): ('CD2', 'CD5'),
        (0, 4): ('CD3', 'CD5'),
        (0, 5): ('CD7', 'CD5'),
        (0, 6): ('CD8', 'CD5'),
        (1, 1): ('CD57', 'CD45'),
        (1, 2): ('CD2', 'CD57'),
        (1, 3): ('CD4', 'CD14'),
        (1, 4): ('CD64', 'CD14'),
        (1, 5): ('CD64', 'CD45'),
        (1, 6): ('CD4', 'CD7'),
    })


def test_to_yaml(layout_1, layout_2):
    assert layout_1.to_yaml() == [
        [['CD5', 'CD19'], ['CD10', 'CD19'], ['CD10', 'CD20'], ['Lambda', 'Kappa']],
        [['CD20', 'CD38'], ['CD45', 'CD38'], ['CD34', 'CD38'], ['CD22', 'CD34']],
    ]
    assert layout_2.to_yaml() == [
        [
            ['CD7', 'CD3'],
            ['CD2', 'CD3'],
            ['CD4', 'CD8'],
            ['CD2', 'CD5'],
            ['CD3', 'CD5'],
            ['CD7', 'CD5'],
            ['CD8', 'CD5'],
        ],
        [
            None,
            ['CD56', 'CD45'],
            ['CD2', 'CD56'],
            ['CD4', 'CD14'],
            ['CD64', 'CD14'],
            ['CD64', 'CD45'],
            ['CD4', 'CD7'],
        ],
    ]
