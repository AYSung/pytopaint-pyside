import pytest

import pandas as pd

from pytopaint.colors import (
    Color,
    _add_red,
    _add_blue,
    _add_green,
    _add_color_to_series,
    add_color_to_selection,
    _subtract_red,
    _subtract_blue,
    _subtract_green,
    _subtract_color_from_series,
    subtract_color_from_selection,
    merge_colors,
    indices_by_color,
    percents_by_colors,
)


@pytest.fixture
def test_df_1() -> pd.DataFrame:
    return pd.DataFrame(
        {
            'color': [
                Color.GREY,
                Color.RED,
                Color.BLUE,
                Color.PURPLE,
                Color.GREEN,
                Color.YELLOW,
                Color.CYAN,
                Color.WHITE,
            ]
        }
    )


@pytest.fixture
def test_df_2() -> pd.DataFrame:
    return pd.DataFrame(
        {
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
        }
    )


def test_add_red():
    assert _add_red(Color.GREY) == Color.RED
    assert _add_red(Color.RED) == Color.RED
    assert _add_red(Color.BLUE) == Color.PURPLE
    assert _add_red(Color.PURPLE) == Color.PURPLE
    assert _add_red(Color.GREEN) == Color.YELLOW
    assert _add_red(Color.YELLOW) == Color.YELLOW
    assert _add_red(Color.CYAN) == Color.WHITE
    assert _add_red(Color.WHITE) == Color.WHITE


def test_add_blue():
    assert _add_blue(Color.GREY) == Color.BLUE
    assert _add_blue(Color.RED) == Color.PURPLE
    assert _add_blue(Color.BLUE) == Color.BLUE
    assert _add_blue(Color.PURPLE) == Color.PURPLE
    assert _add_blue(Color.GREEN) == Color.CYAN
    assert _add_blue(Color.YELLOW) == Color.WHITE
    assert _add_blue(Color.CYAN) == Color.CYAN
    assert _add_blue(Color.WHITE) == Color.WHITE


def test_add_green():
    assert _add_green(Color.GREY) == Color.GREEN
    assert _add_green(Color.RED) == Color.YELLOW
    assert _add_green(Color.BLUE) == Color.CYAN
    assert _add_green(Color.PURPLE) == Color.WHITE
    assert _add_green(Color.GREEN) == Color.GREEN
    assert _add_green(Color.YELLOW) == Color.YELLOW
    assert _add_green(Color.CYAN) == Color.CYAN
    assert _add_green(Color.WHITE) == Color.WHITE


def test_subtract_red():
    assert _subtract_red(Color.GREY) == Color.GREY
    assert _subtract_red(Color.RED) == Color.GREY
    assert _subtract_red(Color.BLUE) == Color.BLUE
    assert _subtract_red(Color.PURPLE) == Color.BLUE
    assert _subtract_red(Color.GREEN) == Color.GREEN
    assert _subtract_red(Color.YELLOW) == Color.GREEN
    assert _subtract_red(Color.CYAN) == Color.CYAN
    assert _subtract_red(Color.WHITE) == Color.CYAN


def test_subtract_blue():
    assert _subtract_blue(Color.GREY) == Color.GREY
    assert _subtract_blue(Color.RED) == Color.RED
    assert _subtract_blue(Color.BLUE) == Color.GREY
    assert _subtract_blue(Color.PURPLE) == Color.RED
    assert _subtract_blue(Color.GREEN) == Color.GREEN
    assert _subtract_blue(Color.YELLOW) == Color.YELLOW
    assert _subtract_blue(Color.CYAN) == Color.GREEN
    assert _subtract_blue(Color.WHITE) == Color.YELLOW


def test_subtract_green():
    assert _subtract_green(Color.GREY) == Color.GREY
    assert _subtract_green(Color.RED) == Color.RED
    assert _subtract_green(Color.BLUE) == Color.BLUE
    assert _subtract_green(Color.PURPLE) == Color.PURPLE
    assert _subtract_green(Color.GREEN) == Color.GREY
    assert _subtract_green(Color.YELLOW) == Color.RED
    assert _subtract_green(Color.CYAN) == Color.BLUE
    assert _subtract_green(Color.WHITE) == Color.PURPLE


def test_add_color_to_series():
    pd.testing.assert_series_equal(
        _add_color_to_series(
            pd.Series(
                [
                    Color.GREY,
                    Color.RED,
                    Color.BLUE,
                    Color.PURPLE,
                    Color.GREEN,
                    Color.YELLOW,
                    Color.CYAN,
                    Color.WHITE,
                ]
            ),
            Color.RED,
        ),
        pd.Series(
            [
                Color.RED,
                Color.RED,
                Color.PURPLE,
                Color.PURPLE,
                Color.YELLOW,
                Color.YELLOW,
                Color.WHITE,
                Color.WHITE,
            ]
        ),
    )
    pd.testing.assert_series_equal(
        _add_color_to_series(
            pd.Series([Color.GREY, Color.RED, Color.BLUE, Color.GREEN]), Color.BLUE
        ),
        pd.Series([Color.BLUE, Color.PURPLE, Color.BLUE, Color.CYAN]),
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
            pd.Series(
                [
                    Color.GREY,
                    Color.RED,
                    Color.BLUE,
                    Color.PURPLE,
                    Color.GREEN,
                    Color.YELLOW,
                    Color.CYAN,
                    Color.WHITE,
                ]
            ),
            Color.RED,
        ),
        pd.Series(
            [
                Color.GREY,
                Color.GREY,
                Color.BLUE,
                Color.BLUE,
                Color.GREEN,
                Color.GREEN,
                Color.CYAN,
                Color.CYAN,
            ]
        ),
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
        pd.Series([Color.GREY, Color.RED, Color.BLUE, Color.PURPLE]),
    )


def test_add_color_to_selection(test_df_1):
    pd.testing.assert_frame_equal(
        add_color_to_selection(
            test_df_1, selection=pd.Index([0, 1, 2, 3, 4, 5, 6, 7]), color=Color.RED
        ),
        pd.DataFrame(
            {
                'color': [
                    Color.RED,
                    Color.RED,
                    Color.PURPLE,
                    Color.PURPLE,
                    Color.YELLOW,
                    Color.YELLOW,
                    Color.WHITE,
                    Color.WHITE,
                ]
            }
        ),
    )
    pd.testing.assert_frame_equal(
        add_color_to_selection(test_df_1, selection=pd.Index([0, 2]), color=Color.RED),
        pd.DataFrame(
            {
                'color': [
                    Color.RED,
                    Color.RED,
                    Color.PURPLE,
                    Color.PURPLE,
                    Color.GREEN,
                    Color.YELLOW,
                    Color.CYAN,
                    Color.WHITE,
                ]
            }
        ),
    )


def test_subtract_color_from_selection(test_df_1):
    pd.testing.assert_frame_equal(
        subtract_color_from_selection(
            test_df_1, selection=pd.Index([0, 1, 2, 3, 4, 5, 6, 7]), color=Color.RED
        ),
        pd.DataFrame(
            {
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
            }
        ),
    )
    pd.testing.assert_frame_equal(
        subtract_color_from_selection(
            test_df_1, selection=pd.Index([0, 2, 5, 6]), color=Color.RED
        ),
        pd.DataFrame(
            {
                'color': [
                    Color.GREY,
                    Color.RED,
                    Color.BLUE,
                    Color.PURPLE,
                    Color.GREEN,
                    Color.GREEN,
                    Color.CYAN,
                    Color.WHITE,
                ]
            }
        ),
    )


def test_merge_color(test_df_1, test_df_2):
    pd.testing.assert_frame_equal(
        merge_colors(test_df_1, [Color.RED, Color.BLUE], Color.GREEN),
        pd.DataFrame(
            {
                'color': [
                    Color.GREY,
                    Color.GREEN,
                    Color.GREEN,
                    Color.PURPLE,
                    Color.GREEN,
                    Color.YELLOW,
                    Color.CYAN,
                    Color.WHITE,
                ]
            }
        ),
    )

    pd.testing.assert_frame_equal(
        merge_colors(test_df_2, [Color.YELLOW, Color.CYAN, Color.GREEN], Color.RED),
        pd.DataFrame(
            {
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
            }
        ),
    )


def test_indices_by_color(test_df_1, test_df_2):
    assert indices_by_color(test_df_1) == {
        Color.GREY: pd.Index([0]),
        Color.RED: pd.Index([1]),
        Color.BLUE: pd.Index([2]),
        Color.PURPLE: pd.Index([3]),
        Color.GREEN: pd.Index([4]),
        Color.YELLOW: pd.Index([5]),
        Color.CYAN: pd.Index([6]),
        Color.WHITE: pd.Index([7]),
    }

    assert indices_by_color(test_df_2)[Color.GREY] == [0]
    assert (indices_by_color(test_df_2)[Color.RED] == [1, 6, 7]).all()
    assert indices_by_color(test_df_2).get(Color.BLUE) is None
    assert indices_by_color(test_df_2).get(Color.PURPLE) is None
    assert indices_by_color(test_df_2)[Color.GREEN] == [2]
    assert indices_by_color(test_df_2)[Color.YELLOW] == [3]
    assert indices_by_color(test_df_2)[Color.CYAN] == [4]
    assert indices_by_color(test_df_2)[Color.WHITE] == [5]


def test_percents_by_colors(test_df_1, test_df_2):
    assert percents_by_colors(test_df_1) == {
        Color.GREY: 1 / 8,
        Color.RED: 1 / 8,
        Color.BLUE: 1 / 8,
        Color.PURPLE: 1 / 8,
        Color.GREEN: 1 / 8,
        Color.YELLOW: 1 / 8,
        Color.CYAN: 1 / 8,
        Color.WHITE: 1 / 8,
    }
    assert percents_by_colors(test_df_2) == {
        Color.GREY: 1 / 8,
        Color.RED: 3 / 8,
        Color.GREEN: 1 / 8,
        Color.YELLOW: 1 / 8,
        Color.CYAN: 1 / 8,
        Color.WHITE: 1 / 8,
    }
