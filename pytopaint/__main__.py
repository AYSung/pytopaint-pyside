import sys

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
)
from PySide6.QtGui import (
    QAction,
    QShortcut,
    QKeySequence,
    QGuiApplication,
)
from PySide6.QtCore import Slot, Qt, Signal

import pandas as pd

from pytopaint.io import test_df, bin_df, read_fcs
from pytopaint.colors import Color
from pytopaint.widgets.painter import Painter
from pytopaint.actions import MenuAction

RESOLUTION = 256


class MainWindow(QMainWindow):
    menuActionTriggered = Signal(int, dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle('PytoPaint')
        self.resolution = 256

        # self.setStyleSheet("QMainWindow { background-color: #121010; }")

        red_shortcut = QShortcut(QKeySequence('F'), self)
        red_shortcut.activated.connect(
            lambda: self.menuActionTriggered.emit(
                MenuAction.SET_ACTIVE, dict(color=Color.RED)
            )
        )
        green_shortcut = QShortcut(QKeySequence('D'), self)
        green_shortcut.activated.connect(
            lambda: self.menuActionTriggered.emit(
                MenuAction.SET_ACTIVE, dict(color=Color.GREEN)
            )
        )
        blue_shortcut = QShortcut(QKeySequence('S'), self)
        blue_shortcut.activated.connect(
            lambda: self.menuActionTriggered.emit(
                MenuAction.SET_ACTIVE, dict(color=Color.BLUE)
            )
        )

        undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
        undo_shortcut.activated.connect(
            lambda: self.menuActionTriggered.emit(MenuAction.UNDO, dict())
        )
        redo_shortcut = QShortcut(QKeySequence('Ctrl+Shift+Z'), self)
        redo_shortcut.activated.connect(
            lambda: self.menuActionTriggered.emit(MenuAction.REDO, dict())
        )

        reset_shortcut = QShortcut(QKeySequence('Ctrl+R'), self)
        reset_shortcut.activated.connect(
            lambda: self.menuActionTriggered.emit(MenuAction.RESET, dict())
        )

        # open_files = QShortcut(QKeySequence.StandardKey.Open, self)
        # open_files.activated.connect(self.open_files)

        menu_bar = self.menuBar()
        # menu_bar.setNativeMenuBar(False)
        file_menu = menu_bar.addMenu('&File')
        # 3. Create and add an Action
        exit_action = QAction('E&xit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # self.load_data()

        painter = Painter(
            bin_df(test_df(), n_bins=self.resolution).assign(color=Color.GREY)
        )
        self.menuActionTriggered.connect(painter.handle_menu_action)

        self.setCentralWidget(painter)

    @Slot()
    def open_files(self):
        # files, _ = QFileDialog.getOpenFileNames(
        #     None, "Select FCS Files", "", "FCS (*.fcs)"
        # )
        file, _ = QFileDialog.getOpenFileName(
            None, 'Select FCS File', '', 'FCS (*.fcs)'
        )

        df = bin_df(read_fcs(file), n_bins=self.resolution).assign(color=Color.GREY)
        # self.load_data(df)
        # self.data_updated.emit(self.df)
        # self.emit_changes()


app = QApplication(sys.argv)
QGuiApplication.styleHints().setColorScheme(Qt.ColorScheme.Dark)
window = MainWindow()
window.show()

app.exec()
