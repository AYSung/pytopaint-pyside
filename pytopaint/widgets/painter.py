from PySide6.QtWidgets import (
    QGridLayout,
    QWidget,
    QSizePolicy,
    QVBoxLayout,
    QLayout,
)
from PySide6.QtGui import (
    QMouseEvent,
    QShortcut,
    QKeySequence,
)
from PySide6.QtCore import Slot, Qt, Signal

import pandas as pd

from pytopaint.selection import get_selection_index
from pytopaint.colors import (
    Color,
    add_color_to_selection,
    subtract_color_from_selection,
    merge_colors,
)
from pytopaint.widgets.biplot import Biplot
from pytopaint.widgets.colorbar import ColorBar
from pytopaint.actions import MenuAction
from pytopaint.layout import get_best_layout, import_layouts
from pytopaint.flowdata import FlowData
from pytopaint.config import appconfig


class Painter(QWidget):
    activeColorChanged = Signal(int)
    dataUpdated = Signal(object)
    highlightsUpdated = Signal(list)
    resizeTriggered = Signal(int, dict)

    def __init__(self, data: FlowData):
        super().__init__()
        self.configure_shortcuts()

        self.data = data

        self.original_df = self.data.binned_df.assign(color=Color.GREY)
        self.df = self.original_df.copy()
        self.undo_history = [self.df.color.copy()]
        self.redo_history = []

        self.highlighted_colors = []

        color_bar = ColorBar()
        color_bar.menuActionTriggered.connect(self.handle_menu_action)
        self.activeColorChanged.connect(color_bar.activeColorChanged)
        self.dataUpdated.connect(color_bar.update_labels)
        self.highlightsUpdated.connect(color_bar.highlightsUpdated)

        biplot_container = QWidget()
        biplot_layout = QGridLayout()
        biplot_layout.setSpacing(5)
        biplot_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)

        biplots = get_best_layout(
            channels=self.df.columns, layouts=import_layouts()
        ).to_grid()

        for coords, label in biplots.items():
            x_label, y_label = label
            row, col = coords

            biplot = Biplot(
                self.df,
                x_label=x_label,
                y_label=y_label,
                axis_ticks=self.data.axis_ticks,
            )
            biplot.pointsSelected.connect(self.handle_selection)
            self.highlightsUpdated.connect(biplot.plot.update_highlighted_colors)
            self.dataUpdated.connect(biplot.set_data)
            self.activeColorChanged.connect(biplot.plot.set_active_color)
            biplot_layout.addWidget(biplot, row, col)
            self.resizeTriggered.connect(biplot.resizeTriggered)

        biplot_container.setLayout(biplot_layout)
        biplot_container.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(color_bar)
        layout.addWidget(biplot_container)
        layout.addStretch()
        self.setLayout(layout)

        self.change_color(Color.RED)
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

        reset_shortcut = QShortcut(QKeySequence('Ctrl+R'), self)
        reset_shortcut.activated.connect(
            lambda: self.handle_menu_action(MenuAction.RESET, dict())
        )

        hide_events_shortcut = QShortcut(QKeySequence('Ctrl+X'), self)
        hide_events_shortcut.activated.connect(
            lambda: self.handle_menu_action(
                MenuAction.HIDE, dict(color=self.active_color)
            )
        )

        isolate_events_shortcut = QShortcut(QKeySequence('Ctrl+Shift+X'), self)
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
                # override existing colors
                self.df.loc[selection, 'color'] = self.active_color

            elif (
                modifiers
                == Qt.KeyboardModifier.ControlModifier
                | Qt.KeyboardModifier.ShiftModifier
            ):
                # override painted colors only
                self.df.loc[
                    self.df.index.isin(selection) & (self.df.color != Color.GREY),
                    'color',
                ] = self.active_color
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

    @Slot(int, dict)
    def handle_menu_action(self, action: MenuAction, kwargs: dict):
        FUNCTION_MAP = {
            MenuAction.SET_ACTIVE: self.change_color,
            MenuAction.ZAP: self.zap_color,
            MenuAction.EXACT_ZAP: self.exact_zap_color,
            MenuAction.ZAP_ALL: self.zap_all,
            MenuAction.MERGE: self.merge_color,
            MenuAction.HIDE: self.hide_color,
            MenuAction.ISOLATE: self.isolate_color,
            MenuAction.UNDO: self.undo_action,
            MenuAction.REDO: self.redo_action,
            MenuAction.RESET: self.reset_df,
            MenuAction.SUBSAMPLE: self.subsample_df,
            MenuAction.HIGHLIGHT: self.handle_highlights,
        }

        FUNCTION_MAP[action](**kwargs)
        if action not in [
            MenuAction.SET_ACTIVE,
            MenuAction.HIGHLIGHT,
            MenuAction.UNDO,
            MenuAction.REDO,
            MenuAction.RESET,
        ]:
            self.record_current_state()
            self.emit_changes()

    def change_color(self, color: Color):
        self.active_color = color
        self.activeColorChanged.emit(self.active_color)

    def zap_color(self, color: Color):
        self.df = subtract_color_from_selection(self.df, color, self.df.index)

    def exact_zap_color(self, color: Color):
        self.df.loc[self.df.color == color, 'color'] = Color.GREY

    def zap_all(self):
        self.df['color'] = Color.GREY

    @Slot(int, int)
    def merge_color(self, source_color: Color, target_color: Color):
        self.df = merge_colors(self.df, [source_color], target_color)

    def hide_color(self, color: Color):
        self.df = self.df.loc[self.df.color != color]

    def isolate_color(self, color: Color):
        self.df = self.df.loc[self.df.color == color].assign(color=Color.GREY)

    def subsample_df(self, n: int):
        self.df = self.df.sample(n, random_state=42)

    @Slot()
    def reset_df(self):
        self.df = self.original_df
        self.record_current_state()
        self.emit_changes()

    def record_current_state(self):
        if self.df.color.equals(self.undo_history[-1]):
            return

        self.undo_history += [self.df.color.copy()]
        self.redo_history = []

    @Slot()
    def undo_action(self):
        if len(self.undo_history) <= 1:
            return

        current_state = self.undo_history.pop()
        previous_state = self.undo_history[-1]
        self.redo_history += [current_state]
        if len(self.df.index) != len(previous_state):
            self.df = self.original_df.loc[previous_state.index].assign(
                color=previous_state
            )
        else:
            self.df['color'] = previous_state

        self.emit_changes()

    @Slot()
    def redo_action(self):
        if not self.redo_history:
            return

        previous_state = self.redo_history.pop()
        self.undo_history += [previous_state]
        if len(self.df.index) != len(previous_state):
            self.df = self.original_df.loc[previous_state.index].assign(
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
        self.original_df = self.data.binned_df.assign(color=Color.GREY)
        self.df = self.original_df.loc[self.df.index].assign(color=self.df['color'])
        self.resizeTriggered.emit(appconfig.resolution, self.data.axis_ticks)
        self.emit_changes()

    @Slot()
    def handle_rescale(self) -> None:
        self.data.rescale()
        self.original_df = self.data.binned_df.assign(color=Color.GREY)
        self.df = self.original_df.loc[self.df.index].assign(color=self.df['color'])
        self.emit_changes()
