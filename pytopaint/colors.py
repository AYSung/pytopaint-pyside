from enum import IntEnum

import pandas as pd


class Color(IntEnum):
    GREY = 0
    BLUE = 1
    GREEN = 2
    RED = 3
    YELLOW = 4
    MAGENTA = 5
    CYAN = 6
    WHITE = 7


COLOR_RGB_MAP = {
    Color.GREY: '#828282',
    Color.BLUE: '#4060ff',
    Color.GREEN: '#46D829',
    Color.RED: '#d12f2f',
    Color.YELLOW: '#EBE824',
    Color.MAGENTA: '#d24fef',
    Color.CYAN: '#43EBF7',
    Color.WHITE: '#E9E9E9',
}

COLOR_NAME_MAP = {
    Color.GREY: 'Grey',
    Color.BLUE: 'Blue',
    Color.GREEN: 'Green',
    Color.RED: 'Red',
    Color.YELLOW: 'Yellow',
    Color.MAGENTA: 'Magenta',
    Color.CYAN: 'Cyan',
    Color.WHITE: 'White',
}

BACKGROUND = '#121010'

ADDITION_COLOR_MAPS = {
    Color.RED: {
        Color.GREY: Color.RED,
        Color.BLUE: Color.MAGENTA,
        Color.GREEN: Color.YELLOW,
        Color.RED: Color.RED,
        Color.YELLOW: Color.YELLOW,
        Color.MAGENTA: Color.MAGENTA,
        Color.CYAN: Color.WHITE,
        Color.WHITE: Color.WHITE,
    },
    Color.GREEN: {
        Color.GREY: Color.GREEN,
        Color.BLUE: Color.CYAN,
        Color.GREEN: Color.GREEN,
        Color.RED: Color.YELLOW,
        Color.YELLOW: Color.YELLOW,
        Color.MAGENTA: Color.WHITE,
        Color.CYAN: Color.CYAN,
        Color.WHITE: Color.WHITE,
    },
    Color.BLUE: {
        Color.GREY: Color.BLUE,
        Color.GREEN: Color.CYAN,
        Color.BLUE: Color.BLUE,
        Color.RED: Color.MAGENTA,
        Color.YELLOW: Color.WHITE,
        Color.MAGENTA: Color.MAGENTA,
        Color.CYAN: Color.CYAN,
        Color.WHITE: Color.WHITE,
    },
    Color.CYAN: {
        Color.GREY: Color.CYAN,
        Color.GREEN: Color.CYAN,
        Color.BLUE: Color.CYAN,
        Color.RED: Color.WHITE,
        Color.YELLOW: Color.WHITE,
        Color.MAGENTA: Color.WHITE,
        Color.CYAN: Color.CYAN,
        Color.WHITE: Color.WHITE,
    },
    Color.MAGENTA: {
        Color.GREY: Color.MAGENTA,
        Color.GREEN: Color.WHITE,
        Color.BLUE: Color.MAGENTA,
        Color.RED: Color.MAGENTA,
        Color.YELLOW: Color.WHITE,
        Color.MAGENTA: Color.MAGENTA,
        Color.CYAN: Color.WHITE,
        Color.WHITE: Color.WHITE,
    },
    Color.YELLOW: {
        Color.GREY: Color.YELLOW,
        Color.GREEN: Color.YELLOW,
        Color.BLUE: Color.WHITE,
        Color.RED: Color.YELLOW,
        Color.YELLOW: Color.YELLOW,
        Color.MAGENTA: Color.WHITE,
        Color.CYAN: Color.WHITE,
        Color.WHITE: Color.WHITE,
    },
    Color.WHITE: {
        Color.GREY: Color.WHITE,
        Color.GREEN: Color.WHITE,
        Color.BLUE: Color.WHITE,
        Color.RED: Color.WHITE,
        Color.YELLOW: Color.WHITE,
        Color.MAGENTA: Color.WHITE,
        Color.CYAN: Color.WHITE,
        Color.WHITE: Color.WHITE,
    },
}

SUBTRACTION_COLOR_MAPS = {
    Color.RED: {
        Color.GREY: Color.GREY,
        Color.BLUE: Color.BLUE,
        Color.GREEN: Color.GREEN,
        Color.RED: Color.GREY,
        Color.YELLOW: Color.GREEN,
        Color.MAGENTA: Color.BLUE,
        Color.CYAN: Color.CYAN,
        Color.WHITE: Color.CYAN,
    },
    Color.BLUE: {
        Color.GREY: Color.GREY,
        Color.RED: Color.RED,
        Color.BLUE: Color.GREY,
        Color.MAGENTA: Color.RED,
        Color.GREEN: Color.GREEN,
        Color.YELLOW: Color.YELLOW,
        Color.CYAN: Color.GREEN,
        Color.WHITE: Color.YELLOW,
    },
    Color.GREEN: {
        Color.GREY: Color.GREY,
        Color.GREEN: Color.GREY,
        Color.BLUE: Color.BLUE,
        Color.RED: Color.RED,
        Color.YELLOW: Color.RED,
        Color.MAGENTA: Color.MAGENTA,
        Color.CYAN: Color.BLUE,
        Color.WHITE: Color.MAGENTA,
    },
    Color.CYAN: {
        Color.GREY: Color.GREY,
        Color.GREEN: Color.GREY,
        Color.BLUE: Color.GREY,
        Color.RED: Color.RED,
        Color.YELLOW: Color.RED,
        Color.MAGENTA: Color.RED,
        Color.CYAN: Color.GREY,
        Color.WHITE: Color.RED,
    },
    Color.MAGENTA: {
        Color.GREY: Color.GREY,
        Color.GREEN: Color.GREEN,
        Color.BLUE: Color.GREY,
        Color.RED: Color.GREY,
        Color.YELLOW: Color.GREEN,
        Color.MAGENTA: Color.GREY,
        Color.CYAN: Color.GREEN,
        Color.WHITE: Color.GREEN,
    },
    Color.YELLOW: {
        Color.GREY: Color.GREY,
        Color.GREEN: Color.GREY,
        Color.BLUE: Color.BLUE,
        Color.RED: Color.GREY,
        Color.YELLOW: Color.GREY,
        Color.MAGENTA: Color.BLUE,
        Color.CYAN: Color.BLUE,
        Color.WHITE: Color.BLUE,
    },
    Color.WHITE: {
        Color.GREY: Color.GREY,
        Color.GREEN: Color.GREY,
        Color.BLUE: Color.GREY,
        Color.RED: Color.GREY,
        Color.YELLOW: Color.GREY,
        Color.MAGENTA: Color.GREY,
        Color.CYAN: Color.GREY,
        Color.WHITE: Color.GREY,
    },
}


def _add_color_to_series(s: pd.Series, color: Color) -> pd.Series:
    return s.map(ADDITION_COLOR_MAPS[color])


def _subtract_color_from_series(s: pd.Series, color: Color) -> pd.Series:
    return s.map(SUBTRACTION_COLOR_MAPS[color])


def add_color_to_selection(
    df: pd.DataFrame, color: Color, selection: pd.Index
) -> pd.DataFrame:
    return df.assign(
        color=df.color.where(
            ~df.index.isin(selection), _add_color_to_series(df.color, color=color)
        ),
    )


def subtract_color_from_selection(
    df: pd.DataFrame, color: Color, selection: pd.Index
) -> pd.DataFrame:
    return df.assign(
        color=df.color.where(
            ~df.index.isin(selection),
            _subtract_color_from_series(df.color, color=color),
        ),
    )


def merge_colors(
    df: pd.DataFrame, source_colors: Color | list[Color], target_color: Color
) -> pd.DataFrame:
    return df.assign(color=df.color.replace(source_colors, target_color))


def indices_by_color(s: pd.Series) -> dict[Color, pd.Index]:
    return {color: pd.Index(index) for color, index in s.groupby(s).groups.items()}


def events_by_colors(df: pd.DataFrame) -> tuple[dict[Color, int], int]:
    return (
        {color: count for color, count in df.color.value_counts().to_dict().items()},
        df.shape[0],
    )
