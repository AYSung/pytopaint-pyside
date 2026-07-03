# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

from functools import wraps

import anndata as ad
import pandas as pd
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import (
    QKeySequence,
    QMouseEvent,
    QShortcut,
)
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from pytopaint.actions import MenuAction
from pytopaint.colors import (
    Color,
    _add_color_to_series,
    _subtract_color_from_series,
    merge_colors,
)
from pytopaint.config import get_resolution
from pytopaint.flowdata import add_umap_dims, set_scale, set_size
from pytopaint.layout import get_best_layout
from pytopaint.selection import get_selection_index
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
    memoryStateReturned = Signal(int, object)
    resizeTriggered = Signal(int)
    stateChanged = Signal(object)

    def __init__(self, data: ad.AnnData):
        super().__init__()
        self.configure_shortcuts()

        self.paint_actions = {
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
            MenuAction.STORE_COLOR: self.store_color,
            MenuAction.STORE_COLOR_AND_CLEAR: self.store_color_and_clear,
            MenuAction.RECALL_COLOR: self.recall_color,
            MenuAction.IMMUNOPHENOTYPE: self.open_immunophenotyper_dialog,
        }

        self.data = data
        self.df = pd.DataFrame(
            self.data.layers['bin'].astype('uint8'), columns=self.data.var_names
        )
        self.state = (
            self.data.obs.reset_index(drop=True).astype({'color': 'uint8'}).copy()
        )
        self.undo_history = [self.state.copy()]
        self.redo_history = []
        self.active_color = Color.BLUE

        self.highlighted_colors = []

        palette = Palette()
        palette.menuActionTriggered.connect(self.handle_menu_action)
        self.colorStateReturned.connect(palette.update_color_memory)
        self.memoryStateReturned.connect(palette.update_memory_slot)
        self.activeColorChanged.connect(palette.activeColorChanged)
        self.stateChanged.connect(palette.update_labels)
        self.highlightsUpdated.connect(palette.highlightsUpdated)
        self.colorPaletteChanged.connect(palette.colorPaletteChanged)

        self.biplot_grid = BiplotGrid(
            df=self.df,
            axis_ticks=self.data.uns['axis_ticks'],
            state=self.state,
            active_color=self.active_color,
        )
        self.biplot_grid.pointsSelected.connect(self.handle_selection)
        self.highlightsUpdated.connect(self.biplot_grid.highlightsUpdated)
        self.stateChanged.connect(self.biplot_grid.stateChanged)
        self.dataChanged.connect(self.biplot_grid.dataChanged)
        self.activeColorChanged.connect(self.biplot_grid.activeColorChanged)
        self.resizeTriggered.connect(self.biplot_grid.resizeTriggered)
        self.colorPaletteChanged.connect(self.biplot_grid.colorPaletteChanged)

        biplot_grid_container = QWidget()
        biplot_grid_container.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        biplot_grid_container.setLayout(self.biplot_grid)

        layout_config = get_best_layout(channels=self.data.var_names)
        self.biplot_grid.update_layout(layout_config)

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(palette)
        layout.addWidget(biplot_grid_container)
        layout.addStretch()
        self.setLayout(layout)

        self.activeColorChanged.emit(self.active_color)
        self.state_changed()

    def configure_shortcuts(self) -> None:
        red_shortcut = QShortcut(QKeySequence('F'), self)
        red_shortcut.activated.connect(
            lambda: self.handle_menu_action(
                MenuAction.SET_ACTIVE, dict(color=Color.RED)
            )
        )
        green_shortcut = QShortcut(QKeySequence('D'), self)
        green_shortcut.activated.connect(
            lambda: self.handle_menu_action(
                MenuAction.SET_ACTIVE, dict(color=Color.GREEN)
            )
        )
        blue_shortcut = QShortcut(QKeySequence('S'), self)
        blue_shortcut.activated.connect(
            lambda: self.handle_menu_action(
                MenuAction.SET_ACTIVE, dict(color=Color.BLUE)
            )
        )
        cyan_shortcut = QShortcut(QKeySequence('Shift+F'), self)
        cyan_shortcut.activated.connect(
            lambda: self.handle_menu_action(
                MenuAction.SET_ACTIVE, dict(color=Color.CYAN)
            )
        )
        magenta_shortcut = QShortcut(QKeySequence('Shift+D'), self)
        magenta_shortcut.activated.connect(
            lambda: self.handle_menu_action(
                MenuAction.SET_ACTIVE, dict(color=Color.MAGENTA)
            )
        )
        yellow_shortcut = QShortcut(QKeySequence('Shift+S'), self)
        yellow_shortcut.activated.connect(
            lambda: self.handle_menu_action(
                MenuAction.SET_ACTIVE, dict(color=Color.YELLOW)
            )
        )
        white_shortcut = QShortcut(QKeySequence('A'), self)
        white_shortcut.activated.connect(
            lambda: self.handle_menu_action(
                MenuAction.SET_ACTIVE, dict(color=Color.WHITE)
            )
        )
        exact_zap_current_color = QShortcut(QKeySequence('E'), self)
        exact_zap_current_color.activated.connect(
            lambda: self.handle_menu_action(
                MenuAction.EXACT_ZAP, dict(color=self.active_color)
            )
        )
        zap_current_color = QShortcut(QKeySequence('Ctrl+E'), self)
        zap_current_color.activated.connect(
            lambda: self.handle_menu_action(
                MenuAction.ZAP, dict(color=self.active_color)
            )
        )
        zap_all = QShortcut(QKeySequence('Ctrl+Shift+E'), self)
        zap_all.activated.connect(
            lambda: self.handle_menu_action(MenuAction.ZAP_ALL, dict())
        )

        undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
        undo_shortcut.activated.connect(
            lambda: self.handle_menu_action(MenuAction.UNDO, dict())
        )
        redo_shortcut = QShortcut(QKeySequence('Ctrl+Shift+Z'), self)
        redo_shortcut.activated.connect(
            lambda: self.handle_menu_action(MenuAction.REDO, dict())
        )

        reset_shortcut = QShortcut(QKeySequence('Ctrl+Shift+R'), self)
        reset_shortcut.activated.connect(
            lambda: self.handle_menu_action(MenuAction.RESET, dict())
        )
        unhide_all_shortcut = QShortcut(QKeySequence('Ctrl+R'), self)
        unhide_all_shortcut.activated.connect(
            lambda: self.handle_menu_action(MenuAction.UNHIDE_ALL, dict())
        )

        hide_events_shortcut = QShortcut(QKeySequence.StandardKey.Backspace, self)
        hide_events_shortcut.activated.connect(
            lambda: self.handle_menu_action(
                MenuAction.HIDE, dict(color=self.active_color)
            )
        )

        isolate_events_shortcut = QShortcut(QKeySequence('Return'), self)
        isolate_events_shortcut.activated.connect(
            lambda: self.handle_menu_action(
                MenuAction.ISOLATE, dict(color=self.active_color)
            )
        )

    @Slot(object, str, str, QMouseEvent)
    def handle_selection(
        self,
        selection_geometry: list[list[int, int]],
        x_label: str,
        y_label: str,
        e: QMouseEvent,
    ):
        modifiers = e.modifiers()

        if e.button() == Qt.MouseButton.MiddleButton:
            if modifiers == Qt.KeyboardModifier.NoModifier:
                self.exact_zap_color(self.active_color)
            elif modifiers == Qt.KeyboardModifier.ShiftModifier:
                self.zap_color(self.active_color)
            elif modifiers == Qt.KeyboardModifier.ControlModifier:
                self.zap_all()
            return

        selection = get_selection_index(
            selection_geometry,
            self.df,
            x_label=x_label,
            y_label=y_label,
        ).intersection(self.state.loc[lambda x: x['visible']].index)
        if selection.empty:
            return

        if e.button() == Qt.MouseButton.LeftButton:
            if modifiers == Qt.KeyboardModifier.NoModifier:
                # add to selection
                self.state.loc[selection, 'color'] = _add_color_to_series(
                    self.state.loc[selection, 'color'], self.active_color
                )

            elif modifiers == Qt.KeyboardModifier.ShiftModifier:
                # ignore unselected points (paint composite color)
                selection = selection.difference(
                    self.state.loc[lambda x: x['color'] == Color.GREY, 'color'].index
                )
                self.state.loc[selection, 'color'] = _add_color_to_series(
                    self.state.loc[selection, 'color'], self.active_color
                )

            elif modifiers == Qt.KeyboardModifier.ControlModifier:
                # ignore painted
                selection = selection.intersection(
                    self.state.loc[lambda x: x['color'] == Color.GREY].index
                )
                self.state.loc[selection, 'color'] = _add_color_to_series(
                    self.state.loc[selection, 'color'], self.active_color
                )

            elif (
                modifiers
                == Qt.KeyboardModifier.ControlModifier
                | Qt.KeyboardModifier.ShiftModifier
            ):
                # override colors
                self.state.loc[selection, 'color'] = self.active_color

        elif e.button() == Qt.MouseButton.RightButton:
            # if not selection.empty:
            if modifiers == Qt.KeyboardModifier.NoModifier:
                # zap color from selection
                selection = selection.intersection(
                    self.state.loc[lambda x: x['color'] == self.active_color].index
                )
                self.state.loc[selection, 'color'] = Color.GREY

            elif modifiers == Qt.KeyboardModifier.ShiftModifier:
                # exact zap color from selection
                self.state.loc[selection, 'color'] = _subtract_color_from_series(
                    self.state.loc[selection, 'color'], self.active_color
                )

            elif modifiers == Qt.KeyboardModifier.ControlModifier:
                # subtract all
                self.state.loc[selection, 'color'] = Color.GREY

        self.record_current_state()

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
    def zap_color(self, color: Color):
        self.state['color'] = _subtract_color_from_series(self.state['color'], color)

    @record_action
    def exact_zap_color(self, color: Color):
        self.state.loc[lambda x: x['visible'] & (x['color'] == color), 'color'] = (
            Color.GREY
        )

    @record_action
    def zap_all(self):
        self.state.loc[lambda x: x['visible'], 'color'] = Color.GREY

    @record_action
    def zap_all_but(self, color: Color):
        self.state.loc[
            lambda x: lambda x: x['visible'] & (x['color'] != color), 'color'
        ] = Color.GREY

    @record_action
    def replace_state(self, memory_state: pd.DataFrame):
        self.state.update(memory_state)

    @record_action
    def merge_state(self, memory_state: pd.DataFrame):
        self.state.update(
            memory_state.loc[
                lambda x: self.state['visible'] & (x['color'] != Color.GREY)
            ]
        )

    def store_state(self, slot: int):
        self.memoryStateReturned.emit(slot, self.state)

    def store_state_and_clear(self, slot: int):
        self.store_state(slot=slot)
        self.zap_all()

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
        self.state['color'] = merge_colors(self.state, [source_color], target_color)

    @record_action
    def unhide_all(self) -> None:
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
        add_umap_dims(self.data)

        umap_df = pd.DataFrame(
            self.data.obsm['umap_bins'],
            columns=['UMAP1', 'UMAP2'],
        )
        self.df = self.df.join(umap_df)

        self.data_changed()

    @record_action
    def reset_df(self):
        self.state['color'] = Color.GREY
        self.state['visible'] = True

    def record_current_state(self):
        if self.state.equals(self.undo_history[-1]):
            return

        self.undo_history += [self.state.copy()]
        self.redo_history = []
        self.state_changed()

    @Slot()
    def undo_paint(self):
        if len(self.undo_history) <= 1:
            return

        current_state: pd.DataFrame = self.undo_history.pop()
        previous_state: pd.DataFrame = self.undo_history[-1]
        self.redo_history += [current_state]
        self.state.update(previous_state)

        self.state_changed()

    @Slot()
    def redo_paint(self):
        if not self.redo_history:
            return

        previous_state: pd.DataFrame = self.redo_history.pop()
        self.undo_history += [previous_state]
        self.state.update(previous_state)

        self.state_changed()

    def data_changed(self):
        self.dataChanged.emit(self.df, self.data.uns['axis_ticks'])

    def state_changed(self):
        self.stateChanged.emit(self.state)

    @Slot(int)
    def handle_highlights(self, color: Color):
        if color not in self.highlighted_colors:
            self.highlighted_colors += [color]
        else:
            self.highlighted_colors.remove(color)

        self.highlightsUpdated.emit(self.highlighted_colors)

    @Slot()
    def handle_resize(self) -> None:
        set_size(self.data)
        self.df = pd.DataFrame(
            self.data.layers['bin'].astype('uint8'), columns=self.data.var_names
        )
        self.resizeTriggered.emit(get_resolution())
        self.data_changed()

    @Slot()
    def handle_rescale(self) -> None:
        set_scale(self.data)
        self.handle_resize()

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
