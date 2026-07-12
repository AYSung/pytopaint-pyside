# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

from dataclasses import dataclass
from importlib import resources
from itertools import chain
from pathlib import Path

import yaml

from pytopaint.flowdata import PHYSICAL_PARAMETERS, sort_channels


@dataclass
class LayoutConfig:
    grid: dict[tuple[int, int], tuple[str, str]]

    @classmethod
    def from_yaml(cls, path: Path):
        with open(path) as stream:
            layout = yaml.safe_load(stream)

        return cls(to_grid(layout))

    @property
    def channels(self) -> list[str]:
        return sort_channels(set(chain(*self.grid.values())))

    @property
    def rows(self) -> int:
        return max([x for x, _ in self.grid.keys()]) + 1

    def columns(self, row: int) -> int:
        return max([y for x, y in self.grid.keys() if x == row]) + 1

    def biplot_score(self, panel: list[str]) -> float:
        return len([
            (x, y) for x, y in self.grid.values() if x in panel and y in panel
        ]) / len([
            (x, y) for x, y in self.grid.values() if x is not None and y is not None
        ])

    def channel_score(self, panel: list[str]) -> float:
        return len([channel for channel in self.channels if channel in panel]) / len(
            panel
        )


def _import_layouts(anchor: str) -> list[LayoutConfig]:

    dir = resources.files(anchor)
    return [
        LayoutConfig.from_yaml(item)
        for item in dir.iterdir()
        if item.is_file()
        and item.name.endswith('.yml')
        and item.name not in ['example.yml']
    ]


def to_grid(
    layout: list[list[tuple[str, str]]],
) -> dict[tuple[int, int], tuple[str, str]]:
    return {
        (x, y): tuple(labels)
        for x, row in enumerate(layout)
        for y, labels in enumerate(row)
        if labels is not None
    }


def import_layouts() -> list[LayoutConfig]:
    return _import_layouts('pytopaint.resources.layouts')


def get_best_layout(channels: list[str]) -> LayoutConfig:
    best_layout_match = get_best_layout_match(channels, layouts=import_layouts())
    return replace_unused_channels(best_layout_match, channels)


def get_best_layout_match(
    channels: list[str], layouts: list[LayoutConfig]
) -> LayoutConfig:
    return sorted(
        layouts, key=lambda x: x.biplot_score(channels) * x.channel_score(channels)
    )[-1]


def replace_unused_channels(
    layout: LayoutConfig, data_channels: list[str]
) -> LayoutConfig:
    def _replace_label(labels: list[str] | None) -> tuple[str, str]:
        if labels is None:
            return None

        x_label, y_label = labels
        if x_label in unused_channel_map.keys():
            x_label = unused_channel_map[x_label]
        if y_label in unused_channel_map.keys():
            y_label = unused_channel_map[y_label]
        return x_label, y_label

    unused_channel_map = dict(
        zip(
            filter(
                lambda x: (
                    x not in set(chain(data_channels, PHYSICAL_PARAMETERS, ['Time']))
                ),
                layout.channels,
            ),
            filter(
                lambda x: (
                    x not in set(chain(layout.channels, PHYSICAL_PARAMETERS, ['Time']))
                ),
                data_channels,
            ),
        )
    )

    return LayoutConfig({
        coord: _replace_label(labels) for coord, labels in layout.grid.items()
    })


def dict_to_yaml(
    layout_grid: dict[tuple[int, int], tuple[str, str]],
) -> list[list[list[str, str]]]:
    def _get_labels(x: int, y: int) -> list[str, str]:
        labels = layout_grid.get((x, y), None)
        return list(labels) if labels is not None else None

    def _columns(row: int) -> int:
        return max([y for x, y in layout_grid.keys() if x == row]) + 1

    rows = max([x for x, _ in layout_grid.keys()]) + 1

    return [[_get_labels(x, y) for y in range(_columns(row=x))] for x in range(rows)]
