import pytest

import pandas as pd

from pytopaint.colors import (
    Color,
    _add_color_to_series,
    add_color_to_selection,
    _subtract_color_from_series,
    subtract_color_from_selection,
    merge_colors,
    indices_by_color,
    events_by_colors,
    ratios_by_color,
)


@pytest.fixture
def test_df_1() -> pd.DataFrame:
    return pd.DataFrame({
        'color': [
            Color.GREY,
            Color.RED,
            Color.BLUE,
            Color.MAGENTA,
            Color.GREEN,
            Color.YELLOW,
            Color.CYAN,
            Color.WHITE,
        ]
    })


@pytest.fixture
def test_df_2() -> pd.DataFrame:
    return pd.DataFrame({
        'color': [
            Color.GREY,
            Color.RED,
            Color.GREEN,
            Color.YELLOW,
            Color.CYAN,
            Color.WHITE,
            Color.RED,
            Color.RED,
        ]
    })


def test_add_color_to_series():
    pd.testing.assert_series_equal(
        _add_color_to_series(
            pd.Series([
                Color.GREY,
                Color.RED,
                Color.BLUE,
                Color.MAGENTA,
                Color.GREEN,
                Color.YELLOW,
                Color.CYAN,
                Color.WHITE,
            ]),
            Color.RED,
        ),
        pd.Series([
            Color.RED,
            Color.RED,
            Color.MAGENTA,
            Color.MAGENTA,
            Color.YELLOW,
            Color.YELLOW,
            Color.WHITE,
            Color.WHITE,
        ]),
    )
    pd.testing.assert_series_equal(
        _add_color_to_series(
            pd.Series([Color.GREY, Color.RED, Color.BLUE, Color.GREEN]), Color.BLUE
        ),
        pd.Series([Color.BLUE, Color.MAGENTA, Color.BLUE, Color.CYAN]),
    )
    pd.testing.assert_series_equal(
        _add_color_to_series(
            pd.Series([Color.GREY, Color.RED, Color.BLUE]), Color.GREEN
        ),
        pd.Series([Color.GREEN, Color.YELLOW, Color.CYAN]),
    )


def test_subtract_color_from_series():
    pd.testing.assert_series_equal(
        _subtract_color_from_series(
            pd.Series([
                Color.GREY,
                Color.RED,
                Color.BLUE,
                Color.MAGENTA,
                Color.GREEN,
                Color.YELLOW,
                Color.CYAN,
                Color.WHITE,
            ]),
            Color.RED,
        ),
        pd.Series([
            Color.GREY,
            Color.GREY,
            Color.BLUE,
            Color.BLUE,
            Color.GREEN,
            Color.GREEN,
            Color.CYAN,
            Color.CYAN,
        ]),
    )
    pd.testing.assert_series_equal(
        _subtract_color_from_series(
            pd.Series([Color.GREY, Color.RED, Color.BLUE, Color.GREEN]), Color.BLUE
        ),
        pd.Series([Color.GREY, Color.RED, Color.GREY, Color.GREEN]),
    )
    pd.testing.assert_series_equal(
        _subtract_color_from_series(
            pd.Series([Color.GREY, Color.RED, Color.BLUE, Color.WHITE]), Color.GREEN
        ),
        pd.Series([Color.GREY, Color.RED, Color.BLUE, Color.MAGENTA]),
    )


def test_add_color_to_selection(test_df_1):
    pd.testing.assert_frame_equal(
        add_color_to_selection(
            test_df_1, color=Color.RED, selection=pd.Index([0, 1, 2, 3, 4, 5, 6, 7])
        ),
        pd.DataFrame({
            'color': [
                Color.RED,
                Color.RED,
                Color.MAGENTA,
                Color.MAGENTA,
                Color.YELLOW,
                Color.YELLOW,
                Color.WHITE,
                Color.WHITE,
            ]
        }),
    )
    pd.testing.assert_frame_equal(
        add_color_to_selection(test_df_1, color=Color.RED, selection=pd.Index([0, 2])),
        pd.DataFrame({
            'color': [
                Color.RED,
                Color.RED,
                Color.MAGENTA,
                Color.MAGENTA,
                Color.GREEN,
                Color.YELLOW,
                Color.CYAN,
                Color.WHITE,
            ]
        }),
    )


def test_subtract_color_from_selection(test_df_1):
    pd.testing.assert_frame_equal(
        subtract_color_from_selection(
            test_df_1, color=Color.RED, selection=pd.Index([0, 1, 2, 3, 4, 5, 6, 7])
        ),
        pd.DataFrame({
            'color': [
                Color.GREY,
                Color.GREY,
                Color.BLUE,
                Color.BLUE,
                Color.GREEN,
                Color.GREEN,
                Color.CYAN,
                Color.CYAN,
            ]
        }),
    )
    pd.testing.assert_frame_equal(
        subtract_color_from_selection(
            test_df_1, color=Color.RED, selection=pd.Index([0, 2, 5, 6])
        ),
        pd.DataFrame({
            'color': [
                Color.GREY,
                Color.RED,
                Color.BLUE,
                Color.MAGENTA,
                Color.GREEN,
                Color.GREEN,
                Color.CYAN,
                Color.WHITE,
            ]
        }),
    )


def test_merge_color(test_df_1, test_df_2):
    pd.testing.assert_frame_equal(
        merge_colors(test_df_1, [Color.RED, Color.BLUE], Color.GREEN),
        pd.DataFrame({
            'color': [
                Color.GREY,
                Color.GREEN,
                Color.GREEN,
                Color.MAGENTA,
                Color.GREEN,
                Color.YELLOW,
                Color.CYAN,
                Color.WHITE,
            ]
        }),
    )

    pd.testing.assert_frame_equal(
        merge_colors(test_df_2, [Color.YELLOW, Color.CYAN, Color.GREEN], Color.RED),
        pd.DataFrame({
            'color': [
                Color.GREY,
                Color.RED,
                Color.RED,
                Color.RED,
                Color.RED,
                Color.WHITE,
                Color.RED,
                Color.RED,
            ]
        }),
    )


def test_indices_by_color(test_df_1, test_df_2):
    assert indices_by_color(test_df_1.color) == {
        Color.GREY: pd.Index([0]),
        Color.RED: pd.Index([1]),
        Color.BLUE: pd.Index([2]),
        Color.MAGENTA: pd.Index([3]),
        Color.GREEN: pd.Index([4]),
        Color.YELLOW: pd.Index([5]),
        Color.CYAN: pd.Index([6]),
        Color.WHITE: pd.Index([7]),
    }

    assert indices_by_color(test_df_2.color)[Color.GREY] == [0]
    assert (indices_by_color(test_df_2.color)[Color.RED] == [1, 6, 7]).all()
    assert indices_by_color(test_df_2.color).get(Color.BLUE) is None
    assert indices_by_color(test_df_2.color).get(Color.MAGENTA) is None
    assert indices_by_color(test_df_2.color)[Color.GREEN] == [2]
    assert indices_by_color(test_df_2.color)[Color.YELLOW] == [3]
    assert indices_by_color(test_df_2.color)[Color.CYAN] == [4]
    assert indices_by_color(test_df_2.color)[Color.WHITE] == [5]


def test_percents_by_colors(test_df_1, test_df_2):
    assert events_by_colors(test_df_1) == (
        {
            Color.GREY: 1,
            Color.RED: 1,
            Color.BLUE: 1,
            Color.MAGENTA: 1,
            Color.GREEN: 1,
            Color.YELLOW: 1,
            Color.CYAN: 1,
            Color.WHITE: 1,
        },
        8,
    )
    assert events_by_colors(test_df_2) == (
        {
            Color.GREY: 1,
            Color.RED: 3,
            Color.GREEN: 1,
            Color.YELLOW: 1,
            Color.CYAN: 1,
            Color.WHITE: 1,
        },
        8,
    )


def test_ratios_by_colors():
    assert ratios_by_color(
        current_color=Color.RED,
        events={
            Color.GREY: 1,
            Color.RED: 1,
            Color.BLUE: 1,
            Color.MAGENTA: 1,
            Color.GREEN: 1,
            Color.YELLOW: 1,
            Color.CYAN: 1,
            Color.WHITE: 1,
        },
    ) == {
        Color.BLUE: 1,
        Color.MAGENTA: 1,
        Color.GREEN: 1,
        Color.YELLOW: 1,
        Color.CYAN: 1,
        Color.WHITE: 1,
    }

    assert ratios_by_color(
        current_color=Color.RED,
        events={
            Color.GREY: 2,
            Color.RED: 1,
            Color.BLUE: 3,
            Color.MAGENTA: 4,
            Color.GREEN: 5,
            Color.YELLOW: 6,
        },
    ) == {
        Color.BLUE: 1 / 3,
        Color.MAGENTA: 1 / 4,
        Color.GREEN: 1 / 5,
        Color.YELLOW: 1 / 6,
    }
    assert ratios_by_color(
        current_color=Color.RED,
        events={
            Color.GREY: 2,
            Color.RED: 4,
            Color.BLUE: 1,
            Color.MAGENTA: 4,
            Color.YELLOW: 0,
        },
    ) == {
        Color.BLUE: 4,
        Color.MAGENTA: 1,
    }
