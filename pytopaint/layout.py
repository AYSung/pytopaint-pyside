from dataclasses import dataclass
from importlib import resources
from itertools import chain

import yaml


@dataclass
class LayoutConfig:
    layout: dict[tuple[int, int], tuple[str, str]]

    @property
    def channels(self) -> set[str]:
        return set(chain(*self.layout.values()))

    def biplot_score(self, panel: list[str]) -> float:
        return len([
            (x, y) for x, y in self.layout.values() if x in panel and y in panel
        ]) / len([
            (x, y) for x, y in self.layout.values() if x is not None and y is not None
        ])

    def channel_score(self, panel: list[str]) -> float:
        return len([channel for channel in self.channels if channel in panel]) / len(
            panel
        )


def _import_layouts(anchor: str) -> list[LayoutConfig]:
    def _read_panel(item) -> LayoutConfig:
        with open(item) as stream:
            layout = yaml.safe_load(stream)

        return LayoutConfig(to_grid(layout))

    dir = resources.files(anchor)
    return [
        _read_panel(item)
        for item in dir.iterdir()
        if item.is_file() and item.name != 'example.yml'
    ]


def to_grid(
    layout: list[list[tuple[str, str]]],
) -> dict[tuple[int, int], tuple[str, str]]:
    return {
        (x, y): biplot
        for x, row in enumerate(layout)
        for y, biplot in enumerate(row)
        if biplot is not None
    }


def import_layouts() -> list[LayoutConfig]:
    return _import_layouts('pytopaint.resources.layouts')


def get_best_layout(channels: list[str], layouts: list[LayoutConfig]) -> LayoutConfig:
    return sorted(
        layouts, key=lambda x: x.biplot_score(channels) * x.channel_score(channels)
    )[-1]
