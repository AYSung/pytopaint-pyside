# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

from functools import wraps

import pandas as pd
from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QGridLayout

from pytopaint.colors import Color
from pytopaint.config import get_resolution, get_zoom_resolution
from pytopaint.flowdata import FlowData
from pytopaint.layout import dict_to_yaml
from pytopaint.widgets.biplot import Biplot
from pytopaint.widgets.zoomplot import ZoomPlot


class BiplotGrid(QGridLayout):
    activeColorChanged = Signal(int)
    colorPaletteChanged = Signal()
    highlightsUpdated = Signal(list)
    updateData = Signal(object, object, object)
    updatePlot = Signal()
    resizeTriggered = Signal(int)
    menuActionTriggered = Signal(int, dict)

    def __init__(
        self,
        data: FlowData,
        state: pd.Series,
        active_color: Color,
        highlighted_colors: list[Color],
    ) -> None:
        super().__init__()
        self.setSpacing(5)
        self.setSizeConstraint(QGridLayout.SizeConstraint.SetFixedSize)

        self.data = data
        self.state = state
        self.active_color = active_color
        self.highlighted_colors = highlighted_colors

        self.zoom_plot = None

        self.update_manager = BiplotUpdateManager(self)

        self.activeColorChanged.connect(self.update_active_color)
        self.highlightsUpdated.connect(self.update_highlighted_colors)

    @Slot(int)
    def update_active_color(self, color: Color) -> None:
        self.active_color = color

    @Slot(list)
    def update_highlighted_colors(self, highlighted_colors: list[Color]) -> None:
        self.highlighted_colors = highlighted_colors

    @staticmethod
    def batch_update(func):
        @wraps(func)
        def wrapper(self: BiplotGrid, *args, **kwargs):
            self.setEnabled(False)

            func(self, *args, **kwargs)

            self.setEnabled(True)
            self.update()

        return wrapper

    @Slot(object, object)
    def update_data(self, data: FlowData) -> None:
        self.data = data
        self.updateData.emit(self.data.binned_df, self.data.axis_ticks, None)

    @Slot(object)
    def update_state(self, state: pd.DataFrame) -> None:
        self.state = state
        self.updateData.emit(None, None, state)

    def new_biplot(
        self,
        labels: tuple[str, str] = (None, None),
    ) -> Biplot:
        x_label, y_label = labels

        biplot = Biplot(
            data=self.data.binned_df,
            axis_ticks=self.data.axis_ticks,
            state=self.state,
            active_color=self.active_color,
            x_label=x_label,
            y_label=y_label,
            resolution=get_resolution(),
            highlighted_colors=self.highlighted_colors,
        )
        self.connect_biplot_signals(biplot)
        return biplot

    def connect_biplot_signals(self, biplot: Biplot) -> None:
        biplot.menuActionTriggered.connect(self.menuActionTriggered)
        biplot.updateFinished.connect(self.update_manager.on_update_finished)
        self.highlightsUpdated.connect(biplot.plot.update_highlighted_colors)
        self.updateData.connect(biplot.update_data)
        self.updatePlot.connect(biplot.plot.set_canvas)
        self.activeColorChanged.connect(biplot.activeColorChanged)
        biplot.removeTriggered.connect(self.remove_biplot)
        self.colorPaletteChanged.connect(biplot.plot.update_plot)
        self.resizeTriggered.connect(biplot.resize)

    def add_biplot(
        self,
        biplot: Biplot,
        coords: tuple[int, int],
    ) -> Biplot:
        self.addWidget(biplot, *coords)

    @batch_update
    def add_rows(self, n_rows: int) -> None:
        col_range = range(self.columns if self.columns > 0 else 1)
        row_range = range(n_rows)
        new_row_coords = [
            (row + self.rows, col) for row in row_range for col in col_range
        ]
        for coords in new_row_coords:
            self.add_biplot(self.new_biplot(), coords)

    @batch_update
    def add_columns(self, n_cols: int) -> None:
        row_range = range(self.rows if self.rows > 0 else 1)
        col_range = range(n_cols)
        new_col_coords = [
            (row, col + self.columns) for col in col_range for row in row_range
        ]

        for coords in new_col_coords:
            self.add_biplot(self.new_biplot(), coords)

    @batch_update
    def remove_empty(self) -> None:
        empty_biplots = [
            biplot for biplot in self.get_biplots() if None in biplot.labels
        ]

        for biplot in empty_biplots:
            self.remove_biplot(biplot)

    @batch_update
    def fill_empty(self) -> None:
        for coords in self.empty_coords:
            self.add_biplot(self.new_biplot(), coords)

    @Slot(object)
    @batch_update
    def remove_biplot(self, biplot: Biplot) -> None:
        self.removeWidget(biplot)
        biplot.deleteLater()

    @batch_update
    def update_layout(
        self,
        grid: dict[tuple[int, int], tuple[str, str]],
    ) -> None:
        for coords, labels in grid.items():
            layout_item = self.itemAtPosition(*coords)
            if layout_item is not None:
                x_label, y_label = labels
                x_label = x_label if x_label in self.data.binned_df.columns else None
                y_label = y_label if y_label in self.data.binned_df.columns else None

                biplot: Biplot = layout_item.widget()
                biplot.set_axes(x_label, y_label)
            else:
                self.add_biplot(self.new_biplot(labels), coords)

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

    @batch_update
    def update_plots(self) -> None:
        self.updatePlot.emit()

    @Slot(str, str)
    def open_zoom(self, x_label: str, y_label: str) -> None:
        self.zoom_plot = Biplot(
            data=self.data.zoom_df,
            axis_ticks=self.data.zoom_axis_ticks,
            state=self.state,
            active_color=self.active_color,
            x_label=x_label,
            y_label=y_label,
            resolution=get_zoom_resolution(),
            highlighted_colors=self.highlighted_colors,
        )
        self.connect_biplot_signals(self.zoom_plot)
        dialog = ZoomPlot(self.zoom_plot, parent=self.parent())
        dialog.menuActionTriggered.connect(self.menuActionTriggered)
        dialog.finished.connect(self.close_zoom)
        dialog.open()

    @Slot()
    def close_zoom(self) -> None:
        self.zoom_plot.deleteLater()
        self.zoom_plot = None

    @property
    def plot_count(self) -> int:
        return self.count() + (self.zoom_plot is not None)


class BiplotUpdateManager:
    def __init__(self, biplot_grid: BiplotGrid):
        self.finished_count = 0
        self.biplot_grid = biplot_grid

    def on_update_finished(self):
        self.finished_count += 1
        if self.finished_count == self.biplot_grid.plot_count:
            self.finished_count = 0
            self.biplot_grid.update_plots()
