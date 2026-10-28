# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

from enum import IntEnum
from typing import NamedTuple

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


class ColorInfo(NamedTuple):
    label: str
    order: int
    related_colors: set[Color]

    def is_zapped_by(self, color: Color) -> bool:
        return color in self.related_colors


COLOR_INFO = {
    Color.GREY: ColorInfo(
        label='Grey',
        order=0,
        related_colors={Color.GREY},
    ),
    Color.BLUE: ColorInfo(
        label='Blue',
        order=1,
        related_colors={Color.BLUE, Color.MAGENTA, Color.CYAN, Color.WHITE},
    ),
    Color.GREEN: ColorInfo(
        label='Green',
        order=2,
        related_colors={Color.GREEN, Color.CYAN, Color.YELLOW, Color.WHITE},
    ),
    Color.RED: ColorInfo(
        label='Red',
        order=3,
        related_colors={Color.RED, Color.YELLOW, Color.MAGENTA, Color.WHITE},
    ),
    Color.YELLOW: ColorInfo(
        label='Yellow',
        order=4,
        related_colors={Color.YELLOW, Color.WHITE},
    ),
    Color.CYAN: ColorInfo(
        label='Cyan',
        order=5,
        related_colors={Color.CYAN, Color.WHITE},
    ),
    Color.MAGENTA: ColorInfo(
        label='Magenta',
        order=6,
        related_colors={Color.MAGENTA, Color.WHITE},
    ),
    Color.WHITE: ColorInfo(
        label='White',
        order=7,
        related_colors={Color.WHITE},
    ),
}


def sort_colors(colors: list[Color]) -> list[Color]:
    return sorted(colors, key=lambda c: COLOR_INFO[c].order)


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


def add_color_to_series(s: pd.Series, color: Color) -> pd.Series:
    s.loc[lambda s: ~s.isin(COLOR_INFO[color].related_colors)] += color
    return s.clip(upper=Color.WHITE)


def subtract_color_from_series(s: pd.Series, color: Color) -> pd.Series:
    s.loc[lambda s: s.isin(COLOR_INFO[color].related_colors)] -= color
    return s.clip(lower=Color.GREY)


def merge_colors(
    s: pd.Series, source_colors: Color | list[Color], target_color: Color
) -> pd.Series:
    return s.replace(source_colors, target_color)


def swap_colors(s: pd.Series, source_color: Color, target_color: Color) -> pd.Series:
    return s.replace({source_color: target_color, target_color: source_color})


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
        return {}
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
    return any(c in COLOR_INFO[color].related_colors for c in events)
