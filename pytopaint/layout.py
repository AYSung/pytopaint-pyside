from dataclasses import dataclass
from importlib import resources
from itertools import chain

import yaml


@dataclass
class LayoutConfig:
    layout: list[list[tuple[str, str]]]

    @property
    def rows(self) -> int:
        return len(self.layout)

    @property
    def cols(self) -> int:
        return max(map(len, self.layout))

    @property
    def channels(self) -> set[str]:
        return set(chain(*chain(*self.layout)))

    def flattened(self) -> list[tuple[str, str]]:
        return list(chain(*[_extend_list(row, self.cols) for row in self.layout]))

    def to_grid(self) -> dict[tuple[int, int], tuple[str, str]]:
        return dict(zip(_to_grid_coordinates(self.rows, self.cols), self.flattened()))

    def biplot_score(self, panel: list[str]) -> float:
        return len([
            (x, y) for x, y in self.flattened() if x in panel and y in panel
        ]) / len([
            (x, y) for x, y in self.flattened() if x is not None and y is not None
        ])

    def channel_score(self, panel: list[str]) -> float:
        return len([channel for channel in self.channels if channel in panel]) / len(
            panel
        )


def _import_layouts(anchor: str) -> list[LayoutConfig]:
    def _read_panel(item) -> LayoutConfig:
        with open(item) as stream:
            layout = yaml.safe_load(stream)

        return LayoutConfig([[(x, y) for x, y in row] for row in layout])

    dir = resources.files(anchor)
    return [
        _read_panel(item)
        for item in dir.iterdir()
        if item.is_file() and item.name != 'example.yml'
    ]


def import_layouts() -> list[LayoutConfig]:
    return _import_layouts('pytopaint.resources.layouts')


def _to_grid_coordinates(
    rows: int,
    cols: int,
) -> list[tuple[int, int]]:
    return [(row, col) for row in range(rows) for col in range(cols)]


def get_best_layout(channels: list[str], layouts: list[LayoutConfig]) -> LayoutConfig:
    return sorted(
        layouts, key=lambda x: x.biplot_score(channels) * x.channel_score(channels)
    )[-1]


def _extend_list(list_: list[tuple[str, str]], target_length: int):
    if len(list_) >= target_length:
        return list_
    else:
        return list_ + [(None, None)] * (target_length - len(list_))
