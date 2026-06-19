import pandas as pd
from functools import wraps

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import (
    QKeySequence,
    QMouseEvent,
    QShortcut,
)
from PySide6.QtWidgets import (
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from pytopaint.actions import MenuAction
from pytopaint.colors import (
    Color,
    add_color_to_selection,
    merge_colors,
    subtract_color_from_selection,
)
from pytopaint.config import appconfig
from pytopaint.flowdata import FlowData
from pytopaint.layout import get_best_layout, LayoutConfig
from pytopaint.selection import get_selection_index
from pytopaint.widgets.biplot import Biplot
from pytopaint.widgets.palette import Palette
from pytopaint.widgets.biplotgrid import BiplotGrid
from pytopaint.widgets.dialogs import add_row_dialog, add_column_dialog


class Painter(QWidget):
    activeColorChanged = Signal(int)
    dataUpdated = Signal(object)
    highlightsUpdated = Signal(list)
    resizeTriggered = Signal(int, dict)
    colorStateReturned = Signal(int, object)
    memoryStateReturned = Signal(int, object)

    def __init__(self, data: FlowData):
        super().__init__()
        self.configure_shortcuts()

        self.paint_actions = {
            MenuAction.SET_ACTIVE: self.change_color,
            MenuAction.ZAP: self.zap_color,
            MenuAction.EXACT_ZAP: self.exact_zap_color,
            MenuAction.ZAP_ALL: self.zap_all,
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
        }

        self.data = data

        self.df = self.data.binned_df.assign(color=Color.GREY)
        self.undo_history = [self.df.color.copy()]
        self.redo_history = []
        self.active_color = Color.BLUE

        self.highlighted_colors = []

        palette = Palette()
        palette.menuActionTriggered.connect(self.handle_menu_action)
        self.colorStateReturned.connect(palette.update_color_memory)
        self.memoryStateReturned.connect(palette.update_memory_slot)
        self.activeColorChanged.connect(palette.activeColorChanged)
        self.dataUpdated.connect(palette.update_labels)
        self.highlightsUpdated.connect(palette.highlightsUpdated)

        biplot_container = QWidget()
        self.biplot_layout = BiplotGrid()

        layout_config = get_best_layout(channels=self.df.columns)

        for coords, labels in layout_config.grid.items():
            self.biplot_layout.add_biplot(self.new_biplot(labels), coords)

        biplot_container.setLayout(self.biplot_layout)
        biplot_container.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(palette)
        layout.addWidget(biplot_container)
        layout.addStretch()
        self.setLayout(layout)

        self.emit_changes()

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
        selection = get_selection_index(
            selection_geometry,
            self.df,
            x_label=x_label,
            y_label=y_label,
        )

        if e.button() == Qt.MouseButton.LeftButton:
            # if not selection.empty:
            if modifiers == Qt.KeyboardModifier.NoModifier:
                # add to selection
                self.df = add_color_to_selection(self.df, self.active_color, selection)

            elif modifiers == Qt.KeyboardModifier.ShiftModifier:
                # ignore unselected points (paint composite color)
                self.df = add_color_to_selection(
                    self.df,
                    self.active_color,
                    selection.difference(
                        self.df.color.loc[lambda s: s == Color.GREY].index
                    ),
                )

            elif modifiers == Qt.KeyboardModifier.ControlModifier:
                # ignore painted
                self.df = add_color_to_selection(
                    self.df,
                    self.active_color,
                    selection.intersection(
                        self.df.color.loc[lambda s: s == Color.GREY].index
                    ),
                )

            elif (
                modifiers
                == Qt.KeyboardModifier.ControlModifier
                | Qt.KeyboardModifier.ShiftModifier
            ):
                # override colors
                self.df.loc[selection, 'color'] = self.active_color

        elif e.button() == Qt.MouseButton.RightButton:
            # if not selection.empty:
            if modifiers == Qt.KeyboardModifier.NoModifier:
                # zap color from selection
                self.df = subtract_color_from_selection(
                    self.df,
                    self.active_color,
                    selection.intersection(
                        self.df.color.loc[lambda s: s == self.active_color].index
                    ),
                )
            elif modifiers == Qt.KeyboardModifier.ShiftModifier:
                # exact zap color from selection
                self.df = subtract_color_from_selection(
                    self.df, self.active_color, selection
                )

            elif modifiers == Qt.KeyboardModifier.ControlModifier:
                # subtract all
                self.df.loc[selection, 'color'] = Color.GREY
        elif e.button() == Qt.MouseButton.MiddleButton:
            if modifiers == Qt.KeyboardModifier.NoModifier:
                self.exact_zap_color(self.active_color)
            elif modifiers == Qt.KeyboardModifier.ShiftModifier:
                self.zap_color(self.active_color)
            elif modifiers == Qt.KeyboardModifier.ControlModifier:
                self.zap_all()

        self.record_current_state()
        self.emit_changes()

    @staticmethod
    def record_action(func):
        @wraps(func)
        def wrapper(self: Painter, *args, **kwargs):
            func(self, *args, **kwargs)
            self.record_current_state()
            self.emit_changes()

        return wrapper

    @Slot(int, dict)
    def handle_menu_action(self, action: MenuAction, kwargs: dict):
        self.paint_actions[action](**kwargs)

    def change_color(self, color: Color):
        self.active_color = color
        self.activeColorChanged.emit(self.active_color)

    @record_action
    def zap_color(self, color: Color):
        self.df = subtract_color_from_selection(self.df, color, self.df.index)

    @record_action
    def exact_zap_color(self, color: Color):
        self.df.loc[self.df.color == color, 'color'] = Color.GREY

    @record_action
    def zap_all(self):
        self.df['color'] = Color.GREY

    @record_action
    def replace_state(self, color_state: pd.Series):
        self.df = self.data.binned_df.loc[color_state.index].assign(color=color_state)

    @record_action
    def merge_state(self, color_state: pd.Series):
        current_colors = self.df.color.copy()
        self.df = self.data.binned_df.loc[
            color_state.index.union(self.df.index)
        ].assign(color=Color.GREY)
        self.df.color.update(current_colors.loc[current_colors != Color.GREY])
        self.df.color.update(color_state.loc[color_state != Color.GREY])

    def store_state(self, slot: int):
        self.memoryStateReturned.emit(slot, self.df.color.copy())

    def store_state_and_clear(self, slot: int):
        self.store_state(slot=slot)
        self.zap_all()

    def store_color(self, color: Color):
        self.colorStateReturned.emit(
            color, self.df.color.loc[lambda s: s == color].copy()
        )

    def store_color_and_clear(self, color: Color):
        self.store_color(color=color)
        self.exact_zap_color(color=color)

    @record_action
    def recall_color(self, color_state: pd.Series):
        self.df.color.update(color_state)

    @record_action
    def merge_color(self, source_color: Color, target_color: Color):
        self.df = merge_colors(self.df, [source_color], target_color)

    @record_action
    def unhide_all(self) -> None:
        current_colors = self.df.color.copy()
        self.df = self.data.binned_df.assign(color=Color.GREY)
        self.df.color.update(current_colors)

    @record_action
    def hide_color(self, color: Color):
        self.df = self.df.loc[self.df.color != color]

    @record_action
    def isolate_color(self, color: Color):
        if (self.df.color == color).any():
            self.df = self.df.loc[self.df.color == color].assign(color=Color.GREY)

    @record_action
    def subsample_df(self, n: int):
        self.df = self.df.sample(n, random_state=42)

    @record_action
    def reset_df(self):
        self.df = self.data.binned_df.assign(color=Color.GREY)
        self.record_current_state()
        self.emit_changes()

    def record_current_state(self):
        if self.df.color.equals(self.undo_history[-1]):
            return

        self.undo_history += [self.df.color.copy()]
        self.redo_history = []

    @Slot()
    def undo_paint(self):
        if len(self.undo_history) <= 1:
            return

        current_state = self.undo_history.pop()
        previous_state = self.undo_history[-1]
        self.redo_history += [current_state]
        if len(self.df.index) != len(previous_state):
            self.df = self.data.binned_df.loc[previous_state.index].assign(
                color=previous_state
            )
        else:
            self.df['color'] = previous_state

        self.emit_changes()

    @Slot()
    def redo_paint(self):
        if not self.redo_history:
            return

        previous_state = self.redo_history.pop()
        self.undo_history += [previous_state]
        if len(self.df.index) != len(previous_state):
            self.df = self.data.binned_df.loc[previous_state.index].assign(
                color=previous_state
            )
        else:
            self.df['color'] = previous_state

        self.emit_changes()

    def emit_changes(self):
        self.dataUpdated.emit(self.df)

    @Slot(int)
    def handle_highlights(self, color: Color):
        if color not in self.highlighted_colors:
            self.highlighted_colors += [color]
        else:
            self.highlighted_colors.remove(color)

        self.highlightsUpdated.emit(self.highlighted_colors)

    @Slot()
    def handle_resize(self) -> None:
        self.df = self.data.binned_df.loc[self.df.index].assign(color=self.df['color'])
        self.resizeTriggered.emit(appconfig.resolution, self.data.axis_ticks)
        self.emit_changes()

    @Slot()
    def handle_rescale(self) -> None:
        self.data.update_scale()
        self.handle_resize()

    def update_layout(self, layout: LayoutConfig) -> None:
        for coords, labels in layout.grid.items():
            layout_item = self.biplot_layout.itemAtPosition(*coords)
            if layout_item is not None:
                x_label, y_label = labels
                x_label = x_label if x_label in self.data.channels else None
                y_label = y_label if y_label in self.data.channels else None

                biplot: Biplot = layout_item.widget()
                biplot.set_axes(x_label, y_label)
            else:
                self.biplot_layout(self.new_biplot(labels), coords)

    def new_biplot(self, labels: tuple[str, str] = (None, None)) -> Biplot:
        x_label, y_label = labels
        biplot = Biplot(
            df=self.df,
            x_label=x_label,
            y_label=y_label,
            axis_ticks=self.data.axis_ticks,
        )
        biplot.pointsSelected.connect(self.handle_selection)
        self.highlightsUpdated.connect(biplot.plot.update_highlighted_colors)
        self.dataUpdated.connect(biplot.set_data)
        self.activeColorChanged.connect(biplot.plot.set_active_color)
        self.resizeTriggered.connect(biplot.resize)
        biplot.plot.set_active_color(self.active_color)
        return biplot

    def layout_to_yaml(self) -> list[list[list[str, str]]]:
        return self.biplot_layout.to_yaml()

    def add_biplot_row(self) -> None:
        n_rows, ok = add_row_dialog(self)

        if not ok:
            return

        col_range = range(
            self.biplot_layout.columns if self.biplot_layout.columns > 0 else 1
        )
        row_range = range(n_rows)
        new_row_coords = [
            (row + self.biplot_layout.rows, col)
            for row in row_range
            for col in col_range
        ]
        for coords in new_row_coords:
            self.biplot_layout.add_biplot(self.new_biplot(), coords)

    def add_biplot_column(self) -> None:
        n_cols, ok = add_column_dialog(self)

        if not ok:
            return

        row_range = range(self.biplot_layout.rows if self.biplot_layout.rows > 0 else 1)
        col_range = range(n_cols)
        new_col_coords = [
            (row, col + self.biplot_layout.columns)
            for col in col_range
            for row in row_range
        ]

        for coords in new_col_coords:
            self.biplot_layout.add_biplot(self.new_biplot(), coords)

    def fill_empty_cells(self) -> None:
        for coords in self.biplot_layout.empty_coords:
            self.biplot_layout.add_biplot(self.new_biplot(), coords)

    def remove_empty_biplots(self) -> None:
        empty_biplots = [
            biplot
            for biplot in self.biplot_layout.get_biplots()
            if None in biplot.labels
        ]
        self.biplot_layout.setEnabled(False)

        for biplot in empty_biplots:
            self.biplot_layout.remove_biplot(biplot)

        self.biplot_layout.setEnabled(True)
        self.biplot_layout.update()
