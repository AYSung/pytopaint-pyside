# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

import cProfile
import pstats
import sys
from io import BytesIO
from itertools import chain
from multiprocessing import freeze_support
from pathlib import Path

import anndata as ad
import flowio
import numpy as np
import yaml
from PySide6.QtCore import (
    QCoreApplication,
    QDir,
    Qt,
    Signal,
    Slot,
)
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
    QLayout,
    QMainWindow,
    QMenu,
    QWidget,
)

from pytopaint.actions import MenuAction
from pytopaint.colors import COLOR_RGB_MAPS
from pytopaint.config import (
    get_color_palette,
    get_window_position,
    set_color_palette,
    set_window_position,
)
from pytopaint.layout import read_yaml
from pytopaint.paths import layout_dir
from pytopaint.widgets.dialogs import (
    PlotScaleDialog,
    PlotSizeDialog,
    about_dialog,
    file_info_dialog,
    report_generator_dialog,
    shortcut_dialog,
    subsample_dialog,
)
from pytopaint.widgets.painter import Painter
from pytopaint.widgets.paintertabs import PainterTabs


class MainWindow(QMainWindow):
    colorPaletteChanged = Signal()
    resizeTriggered = Signal(int)
    rescaleTriggered = Signal(object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle('PytoPaint')

        self.last_dir = QDir.homePath()

        self.setStyleSheet('QMainWindow { background-color: #202020; }')

        self.painter_tabs = PainterTabs()
        self.resizeTriggered.connect(self.painter_tabs.handle_resize)
        self.rescaleTriggered.connect(self.painter_tabs.rescaleTriggered)
        self.colorPaletteChanged.connect(self.painter_tabs.colorPaletteChanged)

        self.configure_menu_bar()
        self.configure_shortcuts()

        central_widget = QWidget()
        central_layout = QGridLayout()
        central_layout.setSpacing(0)
        central_layout.addWidget(self.painter_tabs, 0, 0)
        central_widget.setLayout(central_layout)
        self.layout().setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

        self.setCentralWidget(central_widget)
        self.load_position()

        self.setAcceptDrops(True)

    @Slot()
    def open_file_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(
            None, 'Select File(s)', self.last_dir, 'FCS (*.fcs);;H5AD (*.h5ad)'
        )
        self.open_files(files)

    @Slot()
    def open_dir_dialog(self):
        dir = QFileDialog.getExistingDirectory(
            None, 'Select Directory', self.last_dir, QFileDialog.Option.ShowDirsOnly
        )
        self.open_files_in(dir)

    def open_files_in(self, dir: str):
        files = [item for item in Path(dir).iterdir() if item.is_file()]
        self.open_files(files)

    def open_files(self, files: list[str]):
        for file in files:
            match Path(file).suffix:
                case '.fcs':
                    self.open_fcs(file)
                case '.h5ad':
                    self.open_session(file)

    def open_fcs(self, file: Path):
        try:
            fcs = flowio.FlowData(file)
            painter = Painter.from_fcs(fcs)
            self.painter_tabs.add_painter(painter)
            self.last_dir = str(Path(file).parent)

        except ValueError as e:
            raise e

    def open_session(self, file: Path):
        try:
            adata = ad.io.read_h5ad(file)
            painter = Painter.from_adata(adata)
            self.painter_tabs.add_painter(painter)
            self.last_dir = str(Path(file).parent)

        except ValueError as e:
            raise e

    def save_session(self) -> None:
        painter = self.get_active_painter()
        painter.update_anndata_state()

        file_path, _ = QFileDialog.getSaveFileName(
            parent=None,
            caption='Save Session',
            dir=self.last_dir,
            filter='H5AD (*.h5ad)',
        )
        if not file_path:
            return

        temp_data = painter.data.copy()
        temp_data.layers.clear()
        temp_data.write(filename=file_path, compression='gzip')

    @Slot()
    def export_fcs(self) -> None:
        def _scrub_metadata(metadata: dict[str, str]) -> dict[str, str]:
            return {
                k: v
                for k, v in metadata.items()
                if k
                in flowio.fcs_keywords.FCS_STANDARD_REQUIRED_KEYWORDS
                + ['spill', 'spillover']
            }

        file_path, _ = QFileDialog.getSaveFileName(
            parent=None,
            caption='Export Deidentified FCS',
            dir=self.last_dir,
            filter='FCS (*.fcs)',
        )
        if not file_path:
            return

        painter = self.get_active_painter()
        sample: flowio.FlowData = painter.fcs
        event_mask = painter.state['visible']
        event_matrix: np.ndarray = np.reshape(
            sample.events, (-1, sample.channel_count)
        )[event_mask]

        stream = BytesIO()
        flowio.create_fcs(
            stream,
            event_matrix.flatten(),
            sample.pnn_labels,
            opt_channel_names=sample.pns_labels,
            metadata_dict=_scrub_metadata(sample.text),
        )
        stream.seek(0)

        with open(file_path, 'wb') as f:
            f.write(stream.getbuffer())

    def save_layout(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            parent=None,
            caption='Save Layout',
            dir=str(layout_dir),
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
            None, 'Load Layout', str(layout_dir), 'YAML (*.yml)'
        )
        if not file_path:
            return

        layout = read_yaml(file_path)
        self.get_active_painter().biplot_grid.update_layout(layout.grid)

    def get_active_painter(self) -> Painter:
        return self.painter_tabs.currentWidget()

    def subsample(self) -> None:
        n, ok = subsample_dialog(
            self, total_events=self.get_active_painter().state['visible'].sum()
        )
        if ok:
            self.get_active_painter().handle_menu_action(
                MenuAction.SUBSAMPLE, dict(n=n)
            )

    def resize_plots(self) -> None:
        data = self.get_active_painter().data
        dialog = PlotSizeDialog(self, data.uns.get('bins'))

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.resizeTriggered.emit(dialog.plot_size)

    def rescale_plots(self) -> None:
        data = self.get_active_painter().data
        dialog = PlotScaleDialog(
            parent=self,
            scaling_factor=data.uns.get('scaling_factor'),
            lower_asinh_bound=data.uns.get('lower_asinh_bound'),
            upper_asinh_bound=data.uns.get('upper_asinh_bound'),
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.rescaleTriggered.emit(dialog.scale_config)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        def _expand_url(url: str) -> list[Path]:
            path = Path(url)
            if path.is_dir():
                return [item for item in path.iterdir() if item.is_file()]
            else:
                return [path]

        urls = event.mimeData().urls()
        local_urls = [url.toLocalFile() for url in urls]
        expanded_urls = chain(*map(_expand_url, local_urls))

        self.open_files(expanded_urls)

    def configure_shortcuts(self):
        close_tab_shortcut = QShortcut(QKeySequence('Ctrl+W'), self)
        close_tab_shortcut.activated.connect(
            lambda: self.painter_tabs.tabCloseRequested.emit(
                self.painter_tabs.currentIndex()
            )
        )

        close_all_tabs_shortcut = QShortcut(QKeySequence('Ctrl+Shift+W'), self)
        close_all_tabs_shortcut.activated.connect(self.painter_tabs.close_all_tabs)

    def configure_menu_bar(self):
        def _palette_option(palette: str) -> QAction:
            action = QAction(
                palette,
                self,
                checkable=True,
                checked=(palette == get_color_palette()),
            )
            action.triggered.connect(lambda: self.set_color_palette(action.text()))
            self.colorPaletteChanged.connect(
                lambda: action.setChecked(get_color_palette() == action.text())
            )
            return action

        menu_bar = self.menuBar()
        # menu_bar.setNativeMenuBar(False)
        file_menu = menu_bar.addMenu('&File')

        open_file_action = QAction('&Open File(s)', self)
        open_file_action.setShortcut(QKeySequence.StandardKey.Open)
        open_file_action.triggered.connect(self.open_file_dialog)
        file_menu.addAction(open_file_action)

        open_dir_action = QAction('Open Directory', self)
        open_dir_action.setShortcut(QKeySequence('Ctrl+Shift+O'))
        open_dir_action.triggered.connect(self.open_dir_dialog)
        file_menu.addAction(open_dir_action)

        save_session_action = QAction('&Save Session As', self, enabled=False)
        save_session_action.triggered.connect(self.save_session)
        self.painter_tabs.currentChanged.connect(
            lambda: save_session_action.setEnabled(self.painter_tabs.count())
        )
        file_menu.addAction(save_session_action)

        export_fcs_action = QAction(
            '&Export Deidentified FCS File', self, enabled=False
        )
        export_fcs_action.triggered.connect(self.export_fcs)
        self.painter_tabs.currentChanged.connect(
            lambda: export_fcs_action.setEnabled(
                self.painter_tabs.count() and self.get_active_painter().fcs is not None
            )
        )
        file_menu.addAction(export_fcs_action)

        file_menu.addSeparator()
        color_palette_menu = QMenu('Color Palette')

        palette_options = [
            _palette_option(palette) for palette in COLOR_RGB_MAPS.keys()
        ]
        color_palette_menu.addActions(palette_options)

        file_menu.addMenu(color_palette_menu)
        file_menu.addSeparator()

        file_info_action = QAction('File Info', self, enabled=False)
        file_info_action.triggered.connect(
            lambda: file_info_dialog(self, self.get_active_painter().data).exec()
        )
        self.painter_tabs.currentChanged.connect(
            lambda: file_info_action.setEnabled(self.painter_tabs.count())
        )
        file_menu.addAction(file_info_action)

        exit_action = QAction('E&xit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.setMenuRole(QAction.MenuRole.NoRole)
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

        paint_menu.addSeparator()
        generate_report = QAction('Generate Report Template', self)
        generate_report.triggered.connect(
            lambda: report_generator_dialog(
                self, [painter.data for painter in self.painter_tabs.painters]
            )
        )
        paint_menu.addAction(generate_report)

        layout_menu = menu_bar.addMenu('&Layout')
        layout_menu.setEnabled(False)
        self.painter_tabs.currentChanged.connect(
            lambda: layout_menu.setEnabled(self.painter_tabs.count())
        )
        save_layout_action = QAction('Save Layout...', self)
        save_layout_action.triggered.connect(self.save_layout)
        layout_menu.addAction(save_layout_action)

        load_layout_action = QAction('Load Layout', self)
        load_layout_action.setShortcut('Ctrl+L')
        load_layout_action.triggered.connect(self.load_layout)
        layout_menu.addAction(load_layout_action)
        layout_menu.addSeparator()
        resize_action = QAction('Adjust Plot Size', self)
        resize_action.triggered.connect(self.resize_plots)
        layout_menu.addAction(resize_action)
        rescale_action = QAction('Adjust Plot Scaling', self)
        rescale_action.triggered.connect(self.rescale_plots)
        layout_menu.addAction(rescale_action)
        layout_menu.addSeparator()
        add_biplot_row_action = QAction('Add Row(s)', self)
        add_biplot_row_action.triggered.connect(
            lambda: self.get_active_painter().add_biplot_row()
        )
        layout_menu.addAction(add_biplot_row_action)
        add_biplot_column_action = QAction('Add Column(s)', self)
        add_biplot_column_action.triggered.connect(
            lambda: self.get_active_painter().add_biplot_column()
        )
        layout_menu.addAction(add_biplot_column_action)
        fill_empty_cell_action = QAction('Fill Empty Grid Cells', self)
        fill_empty_cell_action.triggered.connect(
            lambda: self.get_active_painter().fill_empty_cells()
        )
        layout_menu.addAction(fill_empty_cell_action)
        remove_empty_cells_action = QAction('Remove Empty Biplots', self)
        remove_empty_cells_action.triggered.connect(
            lambda: self.get_active_painter().remove_empty_biplots()
        )
        layout_menu.addAction(remove_empty_cells_action)

        analyze_menu = menu_bar.addMenu('&Analyze')
        umap_action = QAction('UMAP', self)
        umap_action.triggered.connect(lambda: self.get_active_painter().add_umap())
        analyze_menu.addAction(umap_action)

        help_menu = menu_bar.addMenu('&Help')

        shortcut_help_action = QAction('Shortcuts', self)
        shortcut_help_action.triggered.connect(lambda: shortcut_dialog(self).exec())
        help_menu.addAction(shortcut_help_action)

        about_action = QAction('About PytoPaint', self)
        about_action.setMenuRole(QAction.MenuRole.NoRole)
        about_action.triggered.connect(lambda: about_dialog(self))
        help_menu.addAction(about_action)

    def closeEvent(self, event):
        set_window_position(self.pos())
        return super().closeEvent(event)

    def set_color_palette(self, palette: str) -> None:
        if palette != get_color_palette():
            set_color_palette(palette)
            self.colorPaletteChanged.emit()

    def load_position(self) -> None:
        position = get_window_position()
        self.move(position.x(), position.y())


def main():
    freeze_support()

    QCoreApplication.setOrganizationName('AYSung')
    QCoreApplication.setApplicationName('PytoPaint')

    app = QApplication(sys.argv)
    QGuiApplication.styleHints().setColorScheme(Qt.ColorScheme.Dark)
    window = MainWindow()
    window.show()

    profiler = cProfile.Profile()
    profiler.enable()

    exit_code = app.exec()
    app.clipboard().clear()

    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats('cumulative')
    stats.print_stats(30)
    profiler.dump_stats('app.prof')

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
