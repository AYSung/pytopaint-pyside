# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

from enum import IntEnum

import pandas as pd

from pytopaint.config import get_color_palette

BACKGROUND = '#121010'


class Color(IntEnum):
    GREY = 0
    BLUE = 1
    GREEN = 2
    CYAN = 3
    RED = 4
    MAGENTA = 5
    YELLOW = 6
    WHITE = 7

    @property
    def label_name(self) -> str:
        return self.name.title()


COLOR_ORDER = {
    Color.GREY: 0,
    Color.BLUE: 1,
    Color.GREEN: 2,
    Color.RED: 3,
    Color.YELLOW: 4,
    Color.MAGENTA: 5,
    Color.CYAN: 6,
    Color.WHITE: 7,
}


def sort_colors(colors: list[Color]) -> list[Color]:
    return sorted(colors, key=lambda c: COLOR_ORDER[c])


COLOR_RGB_MAPS = {
    'Default': {
        Color.GREY: '#606060',
        Color.BLUE: '#1070ff',
        Color.GREEN: '#46D829',
        Color.RED: '#d12f2f',
        Color.YELLOW: '#EBE824',
        Color.MAGENTA: '#d24fef',
        Color.CYAN: '#43EBF7',
        Color.WHITE: '#E9E9E9',
    },
    'Okabe-Ito': {
        Color.GREY: '#828282',
        Color.BLUE: '#0072B2',
        Color.GREEN: '#009E73',
        Color.RED: '#D55E00',
        Color.YELLOW: '#F0E442',
        Color.MAGENTA: '#CC79A7',
        Color.CYAN: '#56B4E9',
        Color.WHITE: '#E9E9E9',
    },
}


def get_color_map() -> dict[Color, str]:
    return COLOR_RGB_MAPS[get_color_palette()]


ZAPPABLE_COLORS = {
    Color.GREY: [],
    Color.RED: [Color.RED, Color.YELLOW, Color.MAGENTA, Color.WHITE],
    Color.BLUE: [Color.BLUE, Color.MAGENTA, Color.CYAN, Color.WHITE],
    Color.GREEN: [Color.GREEN, Color.CYAN, Color.YELLOW, Color.WHITE],
    Color.MAGENTA: [Color.MAGENTA, Color.WHITE],
    Color.CYAN: [Color.CYAN, Color.WHITE],
    Color.YELLOW: [Color.YELLOW, Color.WHITE],
    Color.WHITE: [Color.WHITE],
}


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


def add_color_to_series(s: pd.Series, color: Color) -> pd.Series:
    return s.map(ADDITION_COLOR_MAPS[color])


def subtract_color_from_series(s: pd.Series, color: Color) -> pd.Series:
    return s.map(SUBTRACTION_COLOR_MAPS[color])


def merge_colors(
    s: pd.Series, source_colors: Color | list[Color], target_color: Color
) -> pd.DataFrame:
    return s.replace(source_colors, target_color)


def indices_by_color(s: pd.Series) -> dict[Color, pd.Index]:
    return {
        Color(color): pd.Index(index) for color, index in s.groupby(s).groups.items()
    }


def events_by_color(s: pd.Series) -> dict[Color, int]:
    return {color: index.size for color, index in indices_by_color(s).items()}


def ratios_by_color(
    antecedent_color: Color,
    percents: dict[Color, float],
) -> dict[Color, float]:
    antecedent_percent = percents.get(antecedent_color, 0)
    if antecedent_color == Color.GREY or antecedent_percent == 0:
        return dict()
    else:
        return {
            consequent_color: (
                antecedent_percent / consequent_percent,
                antecedent_percent + consequent_percent,
            )
            for consequent_color, consequent_percent in percents.items()
            if consequent_color not in [Color.GREY, antecedent_color]
        }


def is_zappable(color: Color, events: dict[Color, int]) -> bool:
    return any(c in ZAPPABLE_COLORS[color] for c in events.keys())
