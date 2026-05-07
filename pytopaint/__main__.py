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
    QDragEnterEvent,
    QDropEvent,
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
        self.painter_tabs.setTabsClosable(True)
        self.painter_tabs.tabCloseRequested.connect(self.handle_tab_close)

        central_widget = QWidget()
        central_layout = QGridLayout()
        central_layout.setSpacing(0)
        central_layout.addWidget(self.painter_tabs, 0, 0)
        central_widget.setLayout(central_layout)

        self.setCentralWidget(central_widget)
        self.resize(1920, 1080)

        self.setAcceptDrops(True)
        open_files = QShortcut(QKeySequence.StandardKey.Open, self)
        open_files.activated.connect(self.open_files)

        red_shortcut = QShortcut(QKeySequence('F'), self)
        red_shortcut.activated.connect(
            lambda: self.get_active_painter().handle_menu_action(
                MenuAction.SET_ACTIVE, dict(color=Color.RED)
            )
        )
        green_shortcut = QShortcut(QKeySequence('D'), self)
        green_shortcut.activated.connect(
            lambda: self.get_active_painter().handle_menu_action(
                MenuAction.SET_ACTIVE, dict(color=Color.GREEN)
            )
        )
        blue_shortcut = QShortcut(QKeySequence('S'), self)
        blue_shortcut.activated.connect(
            lambda: self.get_active_painter().handle_menu_action(
                MenuAction.SET_ACTIVE, dict(color=Color.BLUE)
            )
        )

        undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
        undo_shortcut.activated.connect(
            lambda: self.get_active_painter().handle_menu_action(
                MenuAction.UNDO, dict()
            )
        )
        redo_shortcut = QShortcut(QKeySequence('Ctrl+Shift+Z'), self)
        redo_shortcut.activated.connect(
            lambda: self.get_active_painter().handle_menu_action(
                MenuAction.REDO, dict()
            )
        )

        reset_shortcut = QShortcut(QKeySequence('Ctrl+R'), self)
        reset_shortcut.activated.connect(
            lambda: self.get_active_painter().handle_menu_action(
                MenuAction.RESET, dict()
            )
        )

    @Slot()
    def open_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            None, 'Select FCS Files', '', 'FCS (*.fcs)'
        )

        for file in files:
            self.open_file(file)

    def open_file(self, file: Path):
        try:
            file_path = Path(file)
            df = bin_df(read_fcs(file), n_bins=self.resolution).assign(color=Color.GREY)

            painter = Painter(df)

            self.painter_tabs.addTab(painter, file_path.stem)
        except ValueError as e:
            raise e

    def get_active_painter(self) -> Painter:
        return self.painter_tabs.currentWidget()

    @Slot(int)
    def handle_tab_close(self, index: int):
        widget = self.painter_tabs.widget(index)
        self.painter_tabs.removeTab(index)
        if widget is not None:
            widget.deleteLater()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()

        for url in urls:
            self.open_file(url.toLocalFile())


app = QApplication(sys.argv)
QGuiApplication.styleHints().setColorScheme(Qt.ColorScheme.Dark)
window = MainWindow()
window.show()

app.exec()
