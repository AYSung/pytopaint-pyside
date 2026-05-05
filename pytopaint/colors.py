from enum import IntEnum

import pandas as pd


class Color(IntEnum):
    GREY = 0
    RED = 1
    BLUE = 2
    MAGENTA = 3
    GREEN = 4
    YELLOW = 5
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
    Color.MAGENTA: 'MAGENTA',
    Color.CYAN: 'Cyan',
    Color.WHITE: 'White',
}

BACKGROUND = '#121010'

ADDITION_COLOR_MAPS = {
    Color.RED: {
        Color.GREY: Color.RED,
        Color.RED: Color.RED,
        Color.BLUE: Color.MAGENTA,
        Color.MAGENTA: Color.MAGENTA,
        Color.GREEN: Color.YELLOW,
        Color.YELLOW: Color.YELLOW,
        Color.CYAN: Color.WHITE,
        Color.WHITE: Color.WHITE,
    },
    Color.BLUE: {
        Color.GREY: Color.BLUE,
        Color.RED: Color.MAGENTA,
        Color.BLUE: Color.BLUE,
        Color.MAGENTA: Color.MAGENTA,
        Color.GREEN: Color.CYAN,
        Color.YELLOW: Color.WHITE,
        Color.CYAN: Color.CYAN,
        Color.WHITE: Color.WHITE,
    },
    Color.GREEN: {
        Color.GREY: Color.GREEN,
        Color.RED: Color.YELLOW,
        Color.BLUE: Color.CYAN,
        Color.MAGENTA: Color.WHITE,
        Color.GREEN: Color.GREEN,
        Color.YELLOW: Color.YELLOW,
        Color.CYAN: Color.CYAN,
        Color.WHITE: Color.WHITE,
    },
}

SUBTRACTION_COLOR_MAPS = {
    Color.RED: {
        Color.GREY: Color.GREY,
        Color.RED: Color.GREY,
        Color.BLUE: Color.BLUE,
        Color.MAGENTA: Color.BLUE,
        Color.GREEN: Color.GREEN,
        Color.YELLOW: Color.GREEN,
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
        Color.RED: Color.RED,
        Color.BLUE: Color.BLUE,
        Color.MAGENTA: Color.MAGENTA,
        Color.GREEN: Color.GREY,
        Color.YELLOW: Color.RED,
        Color.CYAN: Color.BLUE,
        Color.WHITE: Color.MAGENTA,
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


def indices_by_color(df: pd.DataFrame) -> dict[Color, pd.Index]:
    return {
        color: pd.Index(index) for color, index in df.groupby('color').groups.items()
    }


def percents_by_colors(df: pd.DataFrame) -> dict[Color, float]:
    return {
        color: count / df.shape[0]
        for color, count in df.color.value_counts().to_dict().items()
    }
