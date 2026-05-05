from enum import IntEnum

import pandas as pd


class Color(IntEnum):
    GREY = 0
    RED = 1
    BLUE = 2
    PURPLE = 3
    GREEN = 4
    YELLOW = 5
    CYAN = 6
    WHITE = 7


COLOR_RGB_MAP = {
    Color.GREY: '#828282',
    Color.RED: '#d12f2f',
    Color.GREEN: '#46D829',
    Color.BLUE: '#4060ff',
    Color.PURPLE: '#d24fef',
    Color.YELLOW: '#EBE824',
    Color.CYAN: '#43EBF7',
    Color.WHITE: '#E9E9E9',
}

COLOR_NAME_MAP = {
    Color.GREY: 'Grey',
    Color.RED: 'Red',
    Color.GREEN: 'Green',
    Color.BLUE: 'Blue',
    Color.PURPLE: 'Purple',
    Color.YELLOW: 'Yellow',
    Color.CYAN: 'Cyan',
    Color.WHITE: 'White',
}

BACKGROUND = '#121010'


def _add_red(current_color: Color) -> Color:
    if current_color in {Color.RED, Color.PURPLE, Color.YELLOW, Color.WHITE}:
        return current_color
    else:
        return current_color + Color.RED


def _add_blue(current_color: Color) -> Color:
    if current_color in {Color.BLUE, Color.PURPLE, Color.CYAN, Color.WHITE}:
        return current_color
    else:
        return current_color + Color.BLUE


def _add_green(current_color: Color) -> Color:
    if current_color in {Color.GREEN, Color.YELLOW, Color.CYAN, Color.WHITE}:
        return current_color
    else:
        return current_color + Color.GREEN


def _subtract_red(current_color: Color) -> Color:
    if current_color in {Color.GREY, Color.BLUE, Color.GREEN, Color.CYAN}:
        return current_color
    else:
        return current_color - Color.RED


def _subtract_blue(current_color: Color) -> Color:
    if current_color in {Color.GREY, Color.RED, Color.GREEN, Color.YELLOW}:
        return current_color
    else:
        return current_color - Color.BLUE


def _subtract_green(current_color: Color) -> Color:
    if current_color in {Color.GREY, Color.RED, Color.BLUE, Color.PURPLE}:
        return current_color
    else:
        return current_color - Color.GREEN


def _add_color_to_series(s: pd.Series, color: Color) -> pd.Series:
    map_func = {
        Color.RED: _add_red,
        Color.BLUE: _add_blue,
        Color.GREEN: _add_green,
    }
    return s.map(map_func[color])


def _subtract_color_from_series(s: pd.Series, color: Color) -> pd.Series:
    map_func = {
        Color.RED: _subtract_red,
        Color.BLUE: _subtract_blue,
        Color.GREEN: _subtract_green,
    }
    return s.map(map_func[color])


def add_color_to_selection(
    df: pd.DataFrame, selection: pd.Index, color: Color
) -> pd.DataFrame:
    return df.assign(
        color=df.color.where(
            ~df.index.isin(selection), _add_color_to_series(df.color, color=color)
        ),
    )


def subtract_color_from_selection(
    df: pd.DataFrame, selection: pd.Index, color: Color
) -> pd.DataFrame:
    return df.assign(
        color=df.color.where(
            ~df.index.isin(selection),
            _subtract_color_from_series(df.color, color=color),
        ),
    )


def merge_colors(
    df: pd.DataFrame, source_colors: list[Color], target_color: Color
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
