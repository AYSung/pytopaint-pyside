import sys
from io import BytesIO
from pathlib import Path
import yaml

import flowio
import numpy as np
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import (
    QAction,
    QDragEnterEvent,
    QDropEvent,
    QGuiApplication,
    QKeySequence,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QGridLayout,
    QMainWindow,
    QTabWidget,
    QWidget,
)

from pytopaint.actions import MenuAction
from pytopaint.config import appconfig, import_config, save_config
from pytopaint.flowdata import FlowData
from pytopaint.layout import read_yaml
from pytopaint.widgets.dialogs import (
    PlotScaleDialog,
    about_dialog,
    file_info_dialog,
    resize_plot_dialog,
    save_config_dialog,
    shortcut_dialog,
    subsample_dialog,
)
from pytopaint.widgets.painter import Painter


class MainWindow(QMainWindow):
    resizeTriggered = Signal()
    rescaleTriggered = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle('PytoPaint')

        # self.setStyleSheet('QMainWindow { background-color: #121010; }')

        self.painter_tabs = QTabWidget()
        self.painter_tabs.setTabsClosable(True)
        self.painter_tabs.setElideMode(Qt.TextElideMode.ElideMiddle)
        self.painter_tabs.tabCloseRequested.connect(self.handle_tab_close)

        self.configure_menu_bar()
        self.configure_shortcuts()

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
            self.rescaleTriggered.connect(painter.handle_rescale)
            self.painter_tabs.addTab(painter, file_path.stem)
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

    def save_layout(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            parent=None,
            caption='Save Layout',
            dir='./pytopaint/resources/layouts/',
            filter='YAML (*.yml)',
        )
        if not file_path:
            return

        with open(file_path, 'w') as f:
            yaml.safe_dump(
                self.get_active_painter().layout_to_yaml(),
                f,
                default_flow_style=None,
                sort_keys=False,
                explicit_start=True,
            )

    def load_layout(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            None, 'Load Layout', './pytopaint/resources/layouts/', 'YAML (*.yml)'
        )
        if not file_path:
            return

        layout = read_yaml(file_path)
        self.get_active_painter().update_layout(layout)

    def get_active_painter(self) -> Painter:
        return self.painter_tabs.currentWidget()

    def subsample(self) -> None:
        n, ok = subsample_dialog(self, self.get_active_painter())
        if ok:
            self.get_active_painter().handle_menu_action(
                MenuAction.SUBSAMPLE, dict(n=n)
            )

    def resize_plots(self) -> None:
        pixels, ok = resize_plot_dialog(self)
        if ok:
            appconfig.resolution = pixels
            self.resizeTriggered.emit()

    def rescale_plots(self) -> None:
        dialog = PlotScaleDialog(self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            appconfig.scaling_factor = dialog.scaling_factor
            appconfig.upper_arcsinh_limit = dialog.upper_arcsinh_limit
            appconfig.lower_arcsinh_limit = dialog.lower_arcsinh_limit
            self.rescaleTriggered.emit()

    @Slot(int)
    def handle_tab_close(self, index: int):
        widget = self.painter_tabs.widget(index)
        self.painter_tabs.removeTab(index)
        if widget is not None:
            widget.deleteLater()

    def close_all_tabs(self):
        while self.painter_tabs.count() > 0:
            self.handle_tab_close(0)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()

        for url in urls:
            self.open_file(url.toLocalFile())

    def configure_shortcuts(self):
        close_tab_shortcut = QShortcut(QKeySequence('Ctrl+W'), self)
        close_tab_shortcut.activated.connect(
            lambda: self.painter_tabs.tabCloseRequested.emit(
                self.painter_tabs.currentIndex()
            )
        )

        close_all_tabs_shortcut = QShortcut(QKeySequence('Ctrl+Shift+W'), self)
        close_all_tabs_shortcut.activated.connect(self.close_all_tabs)

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

        file_info_action = QAction('File Info', self, enabled=False)
        file_info_action.triggered.connect(
            lambda: file_info_dialog(self, self.get_active_painter().data.sample).exec()
        )
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
        save_layout_action = QAction('Save Layout...', self)
        save_layout_action.triggered.connect(self.save_layout)
        layout_menu.addAction(save_layout_action)

        load_layout_action = QAction('Load Layout', self)
        load_layout_action.triggered.connect(self.load_layout)
        layout_menu.addAction(load_layout_action)

        plot_menu = menu_bar.addMenu('&Plot')

        resize_action = QAction('Adjust Size', self)
        resize_action.triggered.connect(self.resize_plots)
        plot_menu.addAction(resize_action)

        rescale_action = QAction('Adjust Scaling', self)
        rescale_action.triggered.connect(self.rescale_plots)
        plot_menu.addAction(rescale_action)

        help_menu = menu_bar.addMenu('&Help')

        shortcut_help_action = QAction('Shortcuts', self)
        shortcut_help_action.triggered.connect(lambda: shortcut_dialog(self).exec())
        help_menu.addAction(shortcut_help_action)

        about_action = QAction('About PytoPaint', self)
        about_action.triggered.connect(lambda: about_dialog(self))
        help_menu.addAction(about_action)

    def closeEvent(self, event):
        if appconfig == import_config():
            return

        if save_config_dialog(self):
            save_config()

        return super().closeEvent(event)


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
