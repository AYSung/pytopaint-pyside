import sys

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QGridLayout,
    QWidget,
    QFileDialog,
)
from PySide6.QtGui import (
    QMouseEvent,
    QAction,
    QShortcut,
    QKeySequence,
    QGuiApplication,
)
from PySide6.QtCore import Slot, Qt, Signal

import pandas as pd

from pytopaint.io import test_df, bin_df, read_fcs
from pytopaint.selection import get_selection_index
from pytopaint.colors import (
    Color,
    add_color_to_selection,
    subtract_color_from_selection,
    merge_colors,
    indices_by_color,
    percents_by_colors,
)
from pytopaint.widgets.biplot import Biplot
from pytopaint.widgets.colorbar import ColorBar

RESOLUTION = 256


class MainWindow(QMainWindow):
    selection_updated = Signal(object)
    data_updated = Signal(object)
    percent_selected = Signal(object)
    set_active_color = Signal(int)
    update_active_color = Signal(int)

    def __init__(self):
        super().__init__()
        self.setWindowTitle('PytoPaint')
        self.resolution = 256

        # self.setStyleSheet("QMainWindow { background-color: #121010; }")

        red_shortcut = QShortcut(QKeySequence('S'), self)
        red_shortcut.activated.connect(lambda: self.set_active_color.emit(Color.RED))
        green_shortcut = QShortcut(QKeySequence('D'), self)
        green_shortcut.activated.connect(
            lambda: self.set_active_color.emit(Color.GREEN)
        )
        blue_shortcut = QShortcut(QKeySequence('F'), self)
        blue_shortcut.activated.connect(lambda: self.set_active_color.emit(Color.BLUE))

        self.set_active_color.connect(self.change_color)

        undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
        undo_shortcut.activated.connect(self.undo_action)
        redo_shortcut = QShortcut(QKeySequence('Ctrl+Shift+Z'), self)
        redo_shortcut.activated.connect(self.redo_action)

        reset_shortcut = QShortcut(QKeySequence('Ctrl+R'), self)
        reset_shortcut.activated.connect(self.reset_df)

        open_files = QShortcut(QKeySequence.StandardKey.Open, self)
        open_files.activated.connect(self.open_files)

        menu_bar = self.menuBar()
        # menu_bar.setNativeMenuBar(False)
        file_menu = menu_bar.addMenu('&File')
        # 3. Create and add an Action
        exit_action = QAction('E&xit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        self.load_data(
            bin_df(test_df(), n_bins=self.resolution).assign(color=Color.GREY)
        )

        central_widget = QWidget()
        layout = QGridLayout()
        layout.setSpacing(0)

        color_bar = ColorBar()
        color_bar.merge_color.connect(self.merge_color)
        color_bar.set_active_color.connect(self.set_active_color)
        color_bar.zap_color.connect(self.zap_color)
        color_bar.exact_zap_color.connect(self.exact_zap_color)
        color_bar.hide_color.connect(self.hide_color)
        color_bar.isolate_color.connect(self.isolate_color)
        self.update_active_color.connect(color_bar.update_active_color)
        self.percent_selected.connect(color_bar.update_percent)
        layout.addWidget(color_bar, 0, 0)

        biplot_container = QWidget()
        biplot_layout = QGridLayout()

        biplots = {
            ('FSC-A', 'SSC-A'): (0, 0),
            ('SSC-A', 'CD45 AF700'): (1, 0),
            ('FSC-A', 'FSC-H'): (2, 0),
            ('CD5 BV480', 'CD19'): (0, 1),
            ('CD10', 'CD19'): (0, 2),
            ('CD10', 'CD20'): (0, 3),
            ('m Lambda', 'm Kappa'): (0, 4),
            ('CD20', 'CD38'): (1, 1),
            ('CD45 AF700', 'CD38'): (1, 2),
            ('CD34', 'CD38'): (1, 3),
            ('CD22', 'CD34'): (1, 4),
        }

        for label, coords in biplots.items():
            x_label, y_label = label
            row, col = coords

            biplot = Biplot(self.df, x_label=x_label, y_label=y_label)
            biplot.plot.lasso_selection.connect(self.update_selection)
            color_bar.highlight_color.connect(biplot.plot.update_highlight)
            self.data_updated.connect(biplot.set_data)
            self.selection_updated.connect(biplot.plot.render_plot)
            self.set_active_color.connect(biplot.plot.set_active_color)
            biplot_layout.addWidget(biplot, row, col)

        biplot_container.setLayout(biplot_layout)
        layout.addWidget(biplot_container, 1, 0)

        central_widget.setLayout(layout)

        self.setCentralWidget(central_widget)

        self.set_active_color.emit(Color.RED)
        self.emit_changes()

    @Slot(object, str, str, QMouseEvent)
    def update_selection(
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
            if not selection.empty:
                self.record_current_state()
            if modifiers == Qt.KeyboardModifier.NoModifier:
                # add to selection
                self.df = add_color_to_selection(self.df, selection, self.active_color)

            elif modifiers == Qt.KeyboardModifier.ShiftModifier:
                # ignore unselected points (paint composite color)
                self.df = add_color_to_selection(
                    self.df,
                    selection.difference(
                        self.df.loc[self.df.color == Color.GREY].index
                    ),
                    self.active_color,
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

            self.emit_changes()

        elif e.button() == Qt.MouseButton.RightButton:
            if not selection.empty:
                self.record_current_state()
            if modifiers == Qt.KeyboardModifier.NoModifier:
                # zap color from selection
                self.df = subtract_color_from_selection(
                    self.df,
                    selection.intersection(
                        self.df.loc[self.df.color == self.active_color].index
                    ),
                    self.active_color,
                )
            elif modifiers == Qt.KeyboardModifier.ShiftModifier:
                # exact zap color from selection
                self.df = subtract_color_from_selection(
                    self.df, selection, self.active_color
                )

            elif modifiers == Qt.KeyboardModifier.ControlModifier:
                # subtract all
                self.df.loc[selection, 'color'] = Color.GREY
            self.emit_changes()

        elif e.button() == Qt.MouseButton.MiddleButton:
            if modifiers == Qt.KeyboardModifier.NoModifier:
                self.zap_color(self.active_color)
            elif modifiers == Qt.KeyboardModifier.ShiftModifier:
                self.exact_zap_color(self.active_color)
            elif modifiers == Qt.KeyboardModifier.ControlModifier:
                self.zap_all()

    @Slot(int)
    def zap_color(self, color: Color):
        self.record_current_state()
        self.df.loc[self.df.color == color, 'color'] = Color.GREY
        self.emit_changes()

    @Slot(int)
    def exact_zap_color(self, color: Color):
        self.record_current_state()
        self.df = subtract_color_from_selection(self.df, self.df.index, color)
        self.emit_changes()

    @Slot()
    def zap_all(self):
        self.record_current_state()
        self.df['color'] = Color.GREY
        self.emit_changes()

    def emit_changes(self):
        self.selection_updated.emit(indices_by_color(self.df))
        self.percent_selected.emit(percents_by_colors(self.df))

    @Slot(int)
    def change_color(self, color: Color):
        self.active_color = color
        self.update_active_color.emit(self.active_color)

    def record_current_state(self):
        self.undo_history += [self.df.color.copy()]
        self.redo_history = []

    @Slot()
    def undo_action(self):
        if not self.undo_history:
            return

        previous_state = self.undo_history.pop()
        self.redo_history += [self.df['color'].copy()]
        if len(self.df.index) != len(previous_state):
            self.df = self.original_df.loc[previous_state.index].assign(
                color=previous_state
            )
            self.data_updated.emit(self.df)
        else:
            self.df['color'] = previous_state

        self.emit_changes()

    @Slot()
    def redo_action(self):
        if not self.redo_history:
            return

        next_state = self.redo_history.pop()
        self.undo_history += [self.df['color'].copy()]
        if len(self.df.index) != len(next_state):
            self.df = self.original_df.loc[next_state.index].assign(color=next_state)
            self.data_updated.emit(self.df)
        else:
            self.df['color'] = next_state

        self.emit_changes()

    @Slot(int, int)
    def merge_color(self, source_color: Color, target_color: Color):
        self.record_current_state()
        self.df = merge_colors(self.df, [source_color], target_color)
        self.emit_changes()

    @Slot(int)
    def isolate_color(self, color: Color):
        self.record_current_state()
        self.df = self.df.loc[self.df.color == color].assign(color=Color.GREY)
        self.data_updated.emit(self.df)
        self.emit_changes()

    @Slot(int)
    def hide_color(self, color: Color):
        self.record_current_state()
        self.df = self.df.loc[self.df.color != color]
        self.data_updated.emit(self.df)
        self.emit_changes()

    @Slot()
    def reset_df(self):
        self.record_current_state()
        self.df = self.original_df
        self.data_updated.emit(self.df)

    @Slot()
    def open_files(self):
        # files, _ = QFileDialog.getOpenFileNames(
        #     None, "Select FCS Files", "", "FCS (*.fcs)"
        # )
        file, _ = QFileDialog.getOpenFileName(
            None, 'Select FCS File', '', 'FCS (*.fcs)'
        )

        df = bin_df(read_fcs(file), n_bins=self.resolution).assign(color=Color.GREY)
        self.load_data(df)
        self.data_updated.emit(self.df)
        self.emit_changes()

    def load_data(self, df: pd.DataFrame):
        self.original_df = df
        self.df = df
        self.undo_history = []
        self.redo_history = []


app = QApplication(sys.argv)
QGuiApplication.styleHints().setColorScheme(Qt.ColorScheme.Dark)
window = MainWindow()
window.show()

app.exec()
