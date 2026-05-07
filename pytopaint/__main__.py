import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QTabWidget,
    QWidget,
    QGridLayout,
)
from PySide6.QtGui import (
    QAction,
    QShortcut,
    QKeySequence,
    QGuiApplication,
    QKeyEvent,
)
from PySide6.QtCore import Slot, Qt, Signal

import pandas as pd

from pytopaint.io import bin_df, read_fcs
from pytopaint.colors import Color
from pytopaint.widgets.painter import Painter
from pytopaint.actions import MenuAction

RESOLUTION = 256


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PytoPaint')
        self.resolution = 256

        # self.setStyleSheet("QMainWindow { background-color: #121010; }")

        menu_bar = self.menuBar()
        # menu_bar.setNativeMenuBar(False)
        file_menu = menu_bar.addMenu('&File')
        exit_action = QAction('E&xit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        self.painter_tabs = QTabWidget()

        central_widget = QWidget()
        central_layout = QGridLayout()
        central_layout.setSpacing(0)
        central_layout.addWidget(self.painter_tabs, 0, 0)
        central_widget.setLayout(central_layout)

        self.setCentralWidget(central_widget)
        self.resize(1920, 1080)

        open_files = QShortcut(QKeySequence.StandardKey.Open, self)
        open_files.activated.connect(self.open_files)

        red_shortcut = QShortcut(QKeySequence('F'), self)
        red_shortcut.activated.connect(
            lambda: self.get_active_painter().menuActionTriggered.emit(
                MenuAction.SET_ACTIVE, dict(color=Color.RED)
            )
        )
        green_shortcut = QShortcut(QKeySequence('D'), self)
        green_shortcut.activated.connect(
            lambda: self.get_active_painter().menuActionTriggered.emit(
                MenuAction.SET_ACTIVE, dict(color=Color.GREEN)
            )
        )
        blue_shortcut = QShortcut(QKeySequence('S'), self)
        blue_shortcut.activated.connect(
            lambda: self.get_active_painter().menuActionTriggered.emit(
                MenuAction.SET_ACTIVE, dict(color=Color.BLUE)
            )
        )

        undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
        undo_shortcut.activated.connect(
            lambda: self.get_active_painter().menuActionTriggered.emit(
                MenuAction.UNDO, dict()
            )
        )
        redo_shortcut = QShortcut(QKeySequence('Ctrl+Shift+Z'), self)
        redo_shortcut.activated.connect(
            lambda: self.get_active_painter().menuActionTriggered.emit(
                MenuAction.REDO, dict()
            )
        )

        reset_shortcut = QShortcut(QKeySequence('Ctrl+R'), self)
        reset_shortcut.activated.connect(
            lambda: self.get_active_painter().menuActionTriggered.emit(
                MenuAction.RESET, dict()
            )
        )

    @Slot()
    def open_files(self):
        # files, _ = QFileDialog.getOpenFileNames(
        #     None, "Select FCS Files", "", "FCS (*.fcs)"
        # )
        file, _ = QFileDialog.getOpenFileName(
            None, 'Select FCS File', '', 'FCS (*.fcs)'
        )

        file_path = Path(file)
        df = bin_df(read_fcs(file), n_bins=self.resolution).assign(color=Color.GREY)

        painter = Painter(df)

        self.painter_tabs.addTab(painter, file_path.stem)

    def get_active_painter(self) -> Painter:
        return self.painter_tabs.currentWidget()


app = QApplication(sys.argv)
QGuiApplication.styleHints().setColorScheme(Qt.ColorScheme.Dark)
window = MainWindow()
window.show()

app.exec()
