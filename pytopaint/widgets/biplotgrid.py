# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

from PySide6.QtCore import Slot, Signal
from PySide6.QtWidgets import QGridLayout, QLayout

from pytopaint.layout import dict_to_yaml
from pytopaint.widgets.biplot import Biplot


class BiplotGrid(QGridLayout):
    resizeTriggered = Signal(int)
    colorPaletteChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setSpacing(5)
        self.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

    def add_biplot(self, biplot: Biplot, coords: tuple[int, int]) -> None:
        row, col = coords
        biplot.removeTriggered.connect(self.remove_biplot)
        self.resizeTriggered.connect(biplot.resize)
        self.colorPaletteChanged.connect(biplot.plot.update_plot)
        self.addWidget(biplot, row, col)

    @Slot(object)
    def remove_biplot(self, biplot: Biplot) -> None:
        self.setEnabled(False)

        self.removeWidget(biplot)
        biplot.deleteLater()

        self.setEnabled(True)
        self.update()

    @property
    def rows(self) -> int:
        if self.count() == 0:
            return 0
        return max(self.getItemPosition(i)[0] for i in range(self.count())) + 1

    @property
    def columns(self) -> int:
        if self.count() == 0:
            return 0
        return max(self.getItemPosition(i)[1] for i in range(self.count())) + 1

    def _to_dict(self) -> dict[tuple[int, int], tuple[str, str]]:
        return {
            self._get_biplot_coords(i): self._get_biplot_labels(i)
            for i in range(self.count())
        }

    def to_yaml(self) -> list[list[list[str, str]]]:
        return dict_to_yaml(self._to_dict())

    def _get_biplot(self, index: int) -> Biplot:
        return self.itemAt(index).widget()

    def _get_biplot_labels(self, index: int) -> tuple[str, str]:
        return self._get_biplot(index).labels

    def _get_biplot_coords(self, index: int) -> tuple[int, int]:
        return self.getItemPosition(index)[:2]

    def position_empty(self, coords: tuple[int, int]):
        return self.itemAtPosition(*coords) is None

    @property
    def empty_coords(self) -> list[tuple[int, int]]:
        return [
            (x, y)
            for x in range(self.rows)
            for y in range(self.columns)
            if self.position_empty((x, y))
        ]

    def get_biplots(self) -> list[Biplot]:
        return [self._get_biplot(i) for i in range(self.count())]
