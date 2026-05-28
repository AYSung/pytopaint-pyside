import sys
from pathlib import Path

from io import BytesIO
import flowio
import numpy as np

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QTabWidget,
    QWidget,
    QGridLayout,
    QDialog,
    QVBoxLayout,
    QDialogButtonBox,
    QLabel,
    QLayout,
    QInputDialog,
    QMessageBox,
    QFrame,
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

from pytopaint.flowdata import FlowData, sort_channels
from pytopaint.colors import Color
from pytopaint.widgets.painter import Painter
from pytopaint.actions import MenuAction
from pytopaint.config import appconfig


class MainWindow(QMainWindow):
    resizeTriggered = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle('PytoPaint')

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
        self.move(20, 40)

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

            self.resizeTriggered.connect(painter.handle_resize)
            self.painter_tabs.addTab(painter, file_path.name)
            self.painter_tabs.setCurrentWidget(painter)
        except ValueError as e:
            raise e

    @Slot()
    def export_fcs(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            parent=None,
            caption='Save File',
            dir='',
            filter='FCS (*.fcs)',
        )
        if not file_path:
            return

        painter = self.get_active_painter()
        sample = painter.data.sample
        metadata = sample._get_metadata_for_export(source='raw', include_all=False) | {
            k: v for k, v in sample.metadata.items() if k in ['spill', 'spillover']
        }
        event_mask = np.isin(np.arange(sample.event_count), painter.df.index)
        df = sample.as_dataframe(source='raw', event_mask=event_mask)

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

    def file_info_dialog(self) -> None:
        dialog = QDialog(parent=self)
        dialog.setWindowTitle('File Info')

        sample = self.get_active_painter().data.sample
        file_name = QLabel(f'File Name: {sample.current_filename}')
        event_count = QLabel(f'Event Count: {sample.event_count:,}')
        channels = [
            f'{marker} ({fluor})' if marker else fluor
            for fluor, marker in sample.channels[['pnn', 'pns']].to_records(index=False)
        ]
        channels_label = QLabel(f'Channels: \n{"\n".join(sort_channels(channels))}')

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(dialog.accept)

        layout = QVBoxLayout()
        layout.addWidget(file_name)
        layout.addWidget(event_count)
        layout.addWidget(channels_label)
        layout.addWidget(button_box)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

        dialog.setLayout(layout)

        dialog.exec()

    def about_dialog(self):
        QMessageBox.about(
            self,
            'About PytoPaint',
            'PytoPaint v0.1\n\n\nCreated by Andrew Y. Sung\n\nLast updated May 2026',
        )

    def shortcut_dialog(self):
        def _shortcut_table(shortcuts: list[tuple[str, str]]) -> QWidget:
            table = QWidget()
            grid = QGridLayout()
            grid.setColumnMinimumWidth(0, 200)
            for row, (function, shortcut) in enumerate(shortcuts):
                grid.addWidget(QLabel(function), row, 0)
                grid.addWidget(QLabel(shortcut), row, 1)
            table.setLayout(grid)
            return table

        def _hline() -> QFrame:
            hline = QFrame()
            hline.setFrameShape(QFrame.Shape.HLine)
            return hline

        dialog = QDialog(self)
        dialog.setWindowTitle('Shortcuts')

        layout = QVBoxLayout()
        layout.addWidget(QLabel('<b>Mouse Controls (within biplots):</b>'))
        layout.addWidget(
            _shortcut_table([
                ('Paint events', 'Left-Click'),
                ('Paint non-grey events', 'Shift + Left-Click'),
                ('Override paint colors', 'Ctrl+Left-Click'),
                ('Override non-grey events', 'Ctrl+Shift+Left-Click'),
            ])
        )
        layout.addWidget(
            _shortcut_table([
                ('Exact zap from selection', 'Right-Click'),
                ('Zap from selection', 'Shift + Right-Click'),
                ('Paint grey', 'Ctrl+Right-Click'),
            ])
        )
        layout.addWidget(
            _shortcut_table([
                ('Exact zap color', 'Middle-Click'),
                ('Zap color', 'Shift + Middle-Click'),
            ])
        )
        layout.addWidget(_hline())

        layout.addWidget(QLabel('<b>Keyboard Controls:</b>'))
        layout.addWidget(
            _shortcut_table([
                ('Undo', 'Ctrl + Z'),
                ('Redo', 'Ctrl + Shift + Z'),
                ('Paint Red', 'F'),
                ('Paint Green', 'D'),
                ('Paint Blue', 'S'),
                ('Paint Cyan', 'Shift + F'),
                ('Paint Magenta', 'Shift + D'),
                ('Paint Yellow', 'Shift + S'),
                ('Paint White', 'A'),
                ('Reset Events', 'Ctrl + R'),
                ('Open File(s)', 'Ctrl + O'),
                ('Close Tab', 'Ctrl + W'),
                ('Close Application', 'Ctrl + Q'),
            ])
        )

        layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

        dialog.setLayout(layout)
        dialog.exec()

    def subsample(self) -> None:
        n, ok = QInputDialog.getInt(
            self,
            'Subsample Events',
            'Events to subsample (min. 1000):',
            value=min(10_000, self.get_active_painter().df.shape[0]),
            minValue=1_000,
            maxValue=self.get_active_painter().df.shape[0],
            step=1_000,
        )
        if not ok:
            return

        self.handle_action(MenuAction.SUBSAMPLE, dict(n=n))

    def resize_plots(self) -> None:
        pixels, ok = QInputDialog.getInt(
            self,
            'Change Plot Size',
            'Pixels per dimension (128-256)',
            value=256,
            minValue=128,
            maxValue=256,
            step=16,
        )
        if not ok:
            return

        appconfig.resolution = pixels
        self.resizeTriggered.emit()

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

        close_tab_shortcut = QShortcut(QKeySequence('Ctrl+W'), self)
        close_tab_shortcut.activated.connect(
            lambda: self.painter_tabs.tabCloseRequested.emit(
                self.painter_tabs.currentIndex()
            )
        )

    def configure_menu_bar(self):
        menu_bar = self.menuBar()
        # menu_bar.setNativeMenuBar(False)
        file_menu = menu_bar.addMenu('&File')

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

        file_menu.addSeparator()

        settings_action = QAction('Plot Size', self)
        settings_action.triggered.connect(self.resize_plots)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        file_info_action = QAction('File Info', self, enabled=False)
        file_info_action.triggered.connect(self.file_info_dialog)
        self.painter_tabs.currentChanged.connect(
            lambda: file_info_action.setEnabled(self.painter_tabs.count())
        )
        file_menu.addAction(file_info_action)

        exit_action = QAction('E&xit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        paint_menu = menu_bar.addMenu('&Paint')
        paint_menu.setEnabled(False)
        self.painter_tabs.currentChanged.connect(
            lambda: paint_menu.setEnabled(self.painter_tabs.count())
        )
        subsample_action = QAction('Subsample Data...', self)
        subsample_action.triggered.connect(self.subsample)
        paint_menu.addAction(subsample_action)

        layout_menu = menu_bar.addMenu('&Layout')
        layout_menu.setEnabled(False)
        self.painter_tabs.currentChanged.connect(
            lambda: layout_menu.setEnabled(self.painter_tabs.count())
        )
        # TODO

        help_menu = menu_bar.addMenu('&Help')

        shortcut_help_action = QAction('Shortcuts', self)
        shortcut_help_action.triggered.connect(self.shortcut_dialog)
        help_menu.addAction(shortcut_help_action)

        about_action = QAction('About PytoPaint', self)
        about_action.triggered.connect(self.about_dialog)
        help_menu.addAction(about_action)


def main():
    app = QApplication(sys.argv)
    QGuiApplication.styleHints().setColorScheme(Qt.ColorScheme.Dark)
    window = MainWindow()
    # window.showMaximized()
    window.show()

    app.exec()
    app.clipboard().clear()


if __name__ == '__main__':
    main()
