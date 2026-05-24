import sys
from pathlib import Path

from io import BytesIO
import flowio

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

from pytopaint.flowdata import FlowData
from pytopaint.colors import Color
from pytopaint.widgets.painter import Painter
from pytopaint.actions import MenuAction

RESOLUTION = 256


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PytoPaint')
        self.resolution = 256

        # self.setStyleSheet('QMainWindow { background-color: #121010; }')

        self.painter_tabs = QTabWidget()
        self.painter_tabs.setTabsClosable(True)
        self.painter_tabs.setTabBarAutoHide(True)
        self.painter_tabs.tabCloseRequested.connect(self.handle_tab_close)

        self.configure_menu_bar()
        self.configure_painter_shortcuts()

        central_widget = QWidget()
        central_layout = QGridLayout()
        central_layout.setSpacing(0)
        central_layout.addWidget(self.painter_tabs, 0, 0)
        central_widget.setLayout(central_layout)

        self.setCentralWidget(central_widget)
        self.resize(600, 400)

        self.setAcceptDrops(True)

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
            flowdata = FlowData.from_path(file_path)

            painter = Painter(flowdata)

            self.painter_tabs.addTab(painter, file_path.name)
            self.painter_tabs.setCurrentWidget(painter)
        except ValueError as e:
            raise e

    @Slot()
    def export_fcs(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            parent=None,
            caption='Save File',
            dir='.',
            filter='FCS (*.fcs)',
        )
        if not file_path:
            return

        painter: Painter = self.painter_tabs.widget(self.painter_tabs.currentIndex())
        sample = painter.data.sample
        metadata = sample._get_metadata_for_export(source='raw', include_all=False) | {
            k: v for k, v in sample.metadata.items() if k in ['spill', 'spillover']
        }
        index = painter.df.index
        df = sample.as_dataframe(source='raw').loc[index]

        stream = BytesIO()
        flowio.create_fcs(
            stream,
            df.to_numpy().flatten().tolist(),
            sample.pnn_labels,
            opt_channel_names=sample.pns_labels,
            metadata_dict=metadata,
        )
        stream.seek(0)

        with open(file_path, 'wb') as f:
            f.write(stream.getbuffer())

    def get_active_painter(self) -> Painter:
        return self.painter_tabs.currentWidget()

    def handle_action(self, action: MenuAction, kwargs: dict):
        if self.get_active_painter() is None:
            return

        self.get_active_painter().handle_menu_action(action, kwargs)

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

    def configure_painter_shortcuts(self):
        red_shortcut = QShortcut(QKeySequence('F'), self)
        red_shortcut.activated.connect(
            lambda: self.handle_action(MenuAction.SET_ACTIVE, dict(color=Color.RED))
        )
        green_shortcut = QShortcut(QKeySequence('D'), self)
        green_shortcut.activated.connect(
            lambda: self.handle_action(MenuAction.SET_ACTIVE, dict(color=Color.GREEN))
        )
        blue_shortcut = QShortcut(QKeySequence('S'), self)
        blue_shortcut.activated.connect(
            lambda: self.handle_action(MenuAction.SET_ACTIVE, dict(color=Color.BLUE))
        )
        cyan_shortcut = QShortcut(QKeySequence('Shift+F'), self)
        cyan_shortcut.activated.connect(
            lambda: self.handle_action(MenuAction.SET_ACTIVE, dict(color=Color.CYAN))
        )
        magenta_shortcut = QShortcut(QKeySequence('Shift+D'), self)
        magenta_shortcut.activated.connect(
            lambda: self.handle_action(MenuAction.SET_ACTIVE, dict(color=Color.MAGENTA))
        )
        yellow_shortcut = QShortcut(QKeySequence('Shift+S'), self)
        yellow_shortcut.activated.connect(
            lambda: self.handle_action(MenuAction.SET_ACTIVE, dict(color=Color.YELLOW))
        )
        white_shortcut = QShortcut(QKeySequence('A'), self)
        white_shortcut.activated.connect(
            lambda: self.handle_action(MenuAction.SET_ACTIVE, dict(color=Color.WHITE))
        )

        undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
        undo_shortcut.activated.connect(
            lambda: self.handle_action(MenuAction.UNDO, dict())
        )
        redo_shortcut = QShortcut(QKeySequence('Ctrl+Shift+Z'), self)
        redo_shortcut.activated.connect(
            lambda: self.handle_action(MenuAction.REDO, dict())
        )

        reset_shortcut = QShortcut(QKeySequence('Ctrl+R'), self)
        reset_shortcut.activated.connect(
            lambda: self.handle_action(MenuAction.RESET, dict())
        )

    def configure_menu_bar(self):
        menu_bar = self.menuBar()
        # menu_bar.setNativeMenuBar(False)
        file_menu = menu_bar.addMenu('&File')
        exit_action = QAction('E&xit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        open_file_action = QAction('&Open FCS File(s)', self)
        open_file_action.setShortcut(QKeySequence.StandardKey.Open)
        open_file_action.triggered.connect(self.open_files)
        file_menu.addAction(open_file_action)

        export_fcs_action = QAction('&Export FCS File', self, enabled=False)
        export_fcs_action.triggered.connect(self.export_fcs)
        self.painter_tabs.currentChanged.connect(
            lambda: export_fcs_action.setEnabled(self.painter_tabs.count())
        )
        file_menu.addAction(export_fcs_action)


def main():
    app = QApplication(sys.argv)
    QGuiApplication.styleHints().setColorScheme(Qt.ColorScheme.Dark)
    window = MainWindow()
    window.show()

    app.exec()
    app.clipboard().clear()


if __name__ == '__main__':
    main()
