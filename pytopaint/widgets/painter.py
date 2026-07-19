# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

from collections import deque
from functools import wraps

import anndata as ad
import flowio
import pandas as pd
from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import (
    QCursor,
    QKeySequence,
    QShortcut,
)
from PySide6.QtWidgets import QApplication, QSizePolicy, QVBoxLayout, QWidget

from pytopaint.actions import MenuAction
from pytopaint.colors import (
    Color,
    add_color_to_series,
    merge_colors,
    subtract_color_from_series,
)
from pytopaint.config import get_resolution, get_zoom_resolution
from pytopaint.flowdata import (
    FlowData,
    get_umap_dims,
    umap_transform,
)
from pytopaint.shortcuts import configure_paint_shortcuts
from pytopaint.widgets.biplot import Biplot, DotPlot
from pytopaint.widgets.biplotgrid import BiplotGrid
from pytopaint.widgets.dialogs import (
    add_column_dialog,
    add_row_dialog,
)
from pytopaint.widgets.immunophenotyper import Immunophenotyper
from pytopaint.widgets.palette import Palette


class Painter(QWidget):
    activeColorChanged = Signal(int)
    colorPaletteChanged = Signal()
    colorStateReturned = Signal(int, object)
    dataChanged = Signal(object, object)
    highlightsUpdated = Signal(list)
    stateChanged = Signal(object)
    resizeTriggered = Signal(int)
    zoomTriggered = Signal(str, str)
    menuActionTriggered = Signal(int, dict)

    def __init__(self, data: FlowData, fcs: flowio.FlowData = None):
        super().__init__()
        self.configure_shortcuts()

        self.fcs = fcs
        self.setStyleSheet('* {color: #bababa}')

        self.paint_actions = {
            MenuAction.ADD_COLOR: self.add_color,
            MenuAction.OVERRIDE_COLOR: self.override_color,
            MenuAction.SET_ACTIVE: self.change_color,
            MenuAction.ZAP: self.zap_color,
            MenuAction.EXACT_ZAP: self.exact_zap_color,
            MenuAction.ZAP_ALL: self.zap_all,
            MenuAction.ZAP_ALL_BUT: self.zap_all_but,
            MenuAction.MERGE_COLOR: self.merge_color,
            MenuAction.UNHIDE_ALL: self.unhide_all,
            MenuAction.HIDE: self.hide_color,
            MenuAction.ISOLATE: self.isolate_color,
            MenuAction.UNDO: self.undo_paint,
            MenuAction.REDO: self.redo_paint,
            MenuAction.RESET: self.reset_df,
            MenuAction.SUBSAMPLE: self.subsample_df,
            MenuAction.HIGHLIGHT: self.handle_highlights,
            MenuAction.STORE_STATE: self.store_state,
            MenuAction.STORE_STATE_AND_CLEAR: self.store_state_and_clear,
            MenuAction.REPLACE_STATE: self.replace_state,
            MenuAction.MERGE_STATE: self.merge_state,
            MenuAction.FORGET_STATE: self.forget_state,
            MenuAction.STORE_COLOR: self.store_color,
            MenuAction.STORE_COLOR_AND_CLEAR: self.store_color_and_clear,
            MenuAction.RECALL_COLOR: self.recall_color,
            MenuAction.IMMUNOPHENOTYPE: self.open_immunophenotyper_dialog,
        }

        self.data = data
        self.df = self.data.binned_df
        self.state = self.data.state_df
        self.axis_ticks = self.data.axis_ticks

        self.undo_history = deque()
        self.undo_history.append(self.state.copy())
        self.redo_history = deque()
        self.active_color = Color.BLUE
        self.highlighted_colors = []
        self.menuActionTriggered.connect(self.handle_menu_action)

        self.memory_states = self.data.memory_states
        if 'umap' in self.data.adata.obsm.keys():
            self.load_umap()

        palette = Palette(state=self.state, memory_states=self.memory_states)
        palette.menuActionTriggered.connect(self.menuActionTriggered)
        self.colorStateReturned.connect(palette.update_color_memory)
        self.activeColorChanged.connect(palette.activeColorChanged)
        self.stateChanged.connect(palette.update_labels)
        self.highlightsUpdated.connect(palette.highlightsUpdated)
        self.colorPaletteChanged.connect(palette.colorPaletteChanged)

        self.biplot_grid = BiplotGrid(
            df=self.df,
            zoom_df=self.data.zoom_df,
            axis_ticks=self.data.axis_ticks,
            zoom_axis_ticks=self.data.zoom_axis_ticks,
            state=self.state,
            active_color=self.active_color,
            highlighted_colors=self.highlighted_colors,
        )
        self.biplot_grid.menuActionTriggered.connect(self.menuActionTriggered)
        self.highlightsUpdated.connect(self.biplot_grid.highlightsUpdated)
        self.stateChanged.connect(self.biplot_grid.update_state)
        self.dataChanged.connect(self.biplot_grid.update_data)
        self.resizeTriggered.connect(self.biplot_grid.resizeTriggered)
        self.activeColorChanged.connect(self.biplot_grid.activeColorChanged)
        self.colorPaletteChanged.connect(self.biplot_grid.colorPaletteChanged)
        self.zoomTriggered.connect(self.biplot_grid.open_zoom)

        biplot_grid_container = QWidget()
        biplot_grid_container.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        biplot_grid_container.setLayout(self.biplot_grid)
        self.biplot_grid.update_layout(self.data.layout)

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(palette)
        layout.addWidget(biplot_grid_container)
        layout.addStretch()
        self.setLayout(layout)

        self.activeColorChanged.emit(self.active_color)
        self.highlightsUpdated.emit(self.highlighted_colors)

    @classmethod
    def from_fcs(cls, fcs: flowio.FlowData):
        data = FlowData.from_fcs(fcs)
        return cls(data, fcs)

    @classmethod
    def from_adata(cls, adata: ad.AnnData):
        data = FlowData(adata)
        return cls(data)

    def configure_shortcuts(self) -> None:
        configure_paint_shortcuts(self)

        zoom_biplot_shortcut = QShortcut(QKeySequence('Space'), self)
        zoom_biplot_shortcut.activated.connect(self.zoom_plot)

    @staticmethod
    def record_action(func):
        @wraps(func)
        def wrapper(self: Painter, *args, **kwargs):
            func(self, *args, **kwargs)
            self.record_current_state()

        return wrapper

    @Slot(int, dict)
    def handle_menu_action(self, action: MenuAction, kwargs: dict):
        self.paint_actions[action](**kwargs)

    def change_color(self, color: Color):
        self.active_color = color
        self.activeColorChanged.emit(self.active_color)

    @record_action
    def add_color(self, color: Color, selection: pd.Index):
        self.state.loc[selection, 'color'] = add_color_to_series(
            self.state.loc[selection, 'color'], color
        )

    @record_action
    def override_color(self, color: Color, selection: pd.Index):
        self.state.loc[selection, 'color'] = color

    @record_action
    def zap_color(self, color: Color, selection: pd.Index = None):
        if selection is None:
            self.state['color'] = subtract_color_from_series(self.state['color'], color)
        else:
            self.state.loc[selection, 'color'] = subtract_color_from_series(
                self.state.loc[selection, 'color'], color
            )

    @record_action
    def exact_zap_color(self, color: Color, selection: pd.Index = None):
        if selection is None:
            self.state.loc[self.state['color'] == color, 'color'] = Color.GREY
        else:
            self.state.loc[selection, 'color'] = Color.GREY

    @record_action
    def zap_all(self):
        self.state['color'] = Color.GREY

    @record_action
    def zap_all_but(self, color: Color):
        self.state.loc[self.state['color'] != color, 'color'] = Color.GREY

    @record_action
    def replace_state(self, slot: int):
        self.state.update(self.memory_states[slot])

    @record_action
    def merge_state(self, slot: int):
        self.state.update(
            self.memory_states[slot].loc[
                lambda x: self.state['visible'] & (x['color'] != Color.GREY)
            ]
        )

    def store_state(self, slot: int):
        self.memory_states[slot] = self.state.copy()

    def store_state_and_clear(self, slot: int):
        self.store_state(slot=slot)
        self.zap_all()

    def forget_state(self, slot: int):
        self.memory_states[slot] = None
        print(self.memory_states)

    def store_color(self, color: Color):
        self.colorStateReturned.emit(
            color, self.state.loc[lambda x: x['color'] == color, 'color'].copy()
        )

    def store_color_and_clear(self, color: Color):
        self.store_color(color=color)
        self.exact_zap_color(color=color)

    @record_action
    def recall_color(self, color_state: pd.Series):
        self.state['color'].update(color_state)

    @record_action
    def merge_color(self, source_color: Color, target_color: Color):
        self.state.loc[self.state['visible'], 'color'] = merge_colors(
            self.state.loc[self.state['visible'], 'color'], [source_color], target_color
        )

    @record_action
    def unhide_all(self) -> None:
        self.state.loc[lambda x: ~x['visible'], 'color'] = Color.GREY
        self.state['visible'] = True

    @record_action
    def hide_color(self, color: Color):
        self.state.loc[lambda x: x['color'] == color, 'visible'] = False

    @record_action
    def isolate_color(self, color: Color):
        if not self.state.loc[
            lambda x: (x['color'] == color) & self.state['visible']
        ].empty:
            self.state.loc[lambda x: x['color'] != color, 'visible'] = False
            self.state.loc[lambda x: x['visible'], 'color'] = Color.GREY

    @record_action
    def subsample_df(self, n: int):
        subsample_indices = (
            self.state.loc[lambda x: x['visible']].sample(n, random_state=42).index
        )
        self.state.loc[lambda x: ~x.index.isin(subsample_indices), 'visible'] = False

    def add_umap(self):
        self.data.adata.obsm['umap'] = umap_transform(
            self.data.adata[:, self.data.adata.var['channel_type'] == 'fluoro'].layers[
                'xform'
            ]
        )

        self.load_umap()
        self.data_changed()

    @record_action
    def reset_df(self):
        self.state['color'] = Color.GREY
        self.state['visible'] = True

    def record_current_state(self):
        if self.state.equals(self.undo_history[-1]):
            return

        self.undo_history.append(self.state.copy())
        self.redo_history.clear()
        self.state_changed()

    @Slot()
    def undo_paint(self):
        if len(self.undo_history) <= 1:
            return

        current_state: pd.DataFrame = self.undo_history.pop()
        previous_state: pd.DataFrame = self.undo_history[-1]
        self.redo_history.append(current_state)
        self.state.update(previous_state)

        self.state_changed()

    @Slot()
    def redo_paint(self):
        if not self.redo_history:
            return

        previous_state: pd.DataFrame = self.redo_history.pop()
        self.undo_history.append(previous_state)
        self.state.update(previous_state)

        self.state_changed()

    def data_changed(self):
        self.dataChanged.emit(self.df, self.axis_ticks)

    def state_changed(self):
        self.stateChanged.emit(self.state)

    @Slot(int)
    def handle_highlights(self, color: Color):
        if color not in self.highlighted_colors:
            self.highlighted_colors.append(color)
        else:
            self.highlighted_colors.remove(color)

        self.highlightsUpdated.emit(self.highlighted_colors)

    @Slot()
    def handle_resize(self) -> None:
        resolution = get_resolution()
        self.data.set_size(bins=resolution)

        self.df = self.data.binned_df
        self.axis_ticks = self.data.axis_ticks
        self.resizeTriggered.emit(resolution)
        self.data_changed()

    @Slot(object)
    def handle_rescale(self, scale_config: dict[str, float]) -> None:
        self.data.set_scale(**scale_config)
        self.handle_resize()

    @Slot(object)
    def change_zoom(self) -> None:
        zoom = get_zoom_resolution()
        self.data.set_zoom(bins=zoom)
        self.zoom_axis_ticks = self.data.zoom_axis_ticks
        self.biplot_grid.zoom_axis_ticks = self.zoom_axis_ticks

    def layout_to_yaml(self) -> list[list[list[str, str]]]:
        return self.biplot_grid.to_yaml()

    def add_biplot_row(self) -> None:
        n_rows, ok = add_row_dialog(self)

        if ok:
            self.biplot_grid.add_rows(n_rows)

    def add_biplot_column(self) -> None:
        n_cols, ok = add_column_dialog(self)

        if ok:
            self.biplot_grid.add_columns(n_cols)

    def fill_empty_cells(self) -> None:
        self.biplot_grid.fill_empty()

    def remove_empty_biplots(self) -> None:
        self.biplot_grid.remove_empty()

    def open_immunophenotyper_dialog(self, color: Color):
        dialog = Immunophenotyper(
            data=self.data,
            state=self.state,
            color=color,
            parent=self,
        )
        dialog.exec()

    def update_flowdata_state(self) -> None:
        self.data.update_state(
            self.state, self.memory_states, self.biplot_grid._to_dict()
        )

    def load_umap(self) -> None:
        umap_arr, umap_axis_ticks = get_umap_dims(self.data, get_resolution())
        zoom_umap_arr, zoom_umap_axis_ticks = get_umap_dims(
            self.data, get_zoom_resolution()
        )

        umap_df = pd.DataFrame(
            umap_arr,
            columns=['UMAP1', 'UMAP2'],
        )
        self.axis_ticks = self.axis_ticks | umap_axis_ticks
        self.biplot_grid.zoom_axis_ticks = (
            self.biplot_grid.zoom_axis_ticks | zoom_umap_axis_ticks
        )
        self.df = self.df.join(umap_df)
        self.biplot_grid.zoom_df = self.biplot_grid.zoom_df.join(
            pd.DataFrame(zoom_umap_arr, columns=['UMAP1', 'UMAP2'])
        )

    def zoom_plot(self) -> None:
        cursor_position = QCursor().pos()
        widget = QApplication.widgetAt(cursor_position)
        if isinstance(widget, DotPlot):
            parent_widget: Biplot = widget.parentWidget()
            self.zoomTriggered.emit(
                parent_widget.x_axis.label, parent_widget.y_axis.label
            )
