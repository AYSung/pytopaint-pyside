from collections.abc import Iterable
from io import BytesIO
from itertools import chain
from pathlib import Path

import anndata as ad
import flowio
import yaml
from PySide6.QtCore import (
    QDir,
    QObject,
    Qt,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QProgressDialog,
)

from pytopaint.layout import LayoutConfig
from pytopaint.paths import layout_dir
from pytopaint.widgets.painter import Painter


class IOManager(QObject):
    fileOpened = Signal(object)
    finished = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.last_open_dir = QDir.homePath()
        self.last_save_dir = QDir.homePath()
        self.file_parsers = {'.fcs': open_fcs, '.h5ad': open_session}

    def open_files(self, files: list[Path]) -> None:
        progress = QProgressDialog(
            'Opening files...', 'Cancel', 0, len(files), self.parent()
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)

        progress.show()
        self.finished.emit(False)
        for i, file in enumerate(files, start=1):
            if progress.wasCanceled():
                break

            try:
                painter = self.file_parsers[file.suffix.lower()](file)
                self.fileOpened.emit(painter)
            except ValueError:
                print(f'error opening {file}')
            finally:
                progress.setValue(i)
                QApplication.processEvents()

        self.finished.emit(True)

    @Slot()
    def open_files_dialog(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            None, 'Select File(s)', self.last_open_dir, 'FCS (*.fcs);;H5AD (*.h5ad)'
        )

        paths = filter_valid_files(map(Path, files))
        if not paths:
            return

        self.open_files(paths)
        self.last_open_dir = str(paths[-1].parent)

    @Slot()
    def open_dir_dialog(self) -> None:
        dir = QFileDialog.getExistingDirectory(
            None,
            'Select Directory',
            self.last_open_dir,
            QFileDialog.Option.ShowDirsOnly,
        )
        dir = Path(dir)
        files = get_child_files(dir)
        if not files:
            return

        self.open_files(files)
        self.last_open_dir = str(dir.parent)

    def open_files_from_urls(self, urls: list[QUrl]) -> None:
        paths = get_files_from_urls(urls)
        self.open_files(paths)
        self.last_open_dir = str(paths[-1].parent)

    def export_fcs(self, painter: Painter) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            parent=None,
            caption='Export Deidentified FCS',
            dir=self.last_save_dir,
            filter='FCS (*.fcs)',
        )
        if not file_path:
            return

        sample: flowio.FlowData = painter.fcs
        event_mask = painter.state['visible']
        event_matrix = sample.as_array()[event_mask]

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

        self.last_save_dir = str(Path(file_path).parent)

    def save_session(self, painter: Painter) -> None:
        painter.update_anndata_state()

        file_path, _ = QFileDialog.getSaveFileName(
            parent=None,
            caption='Save Session',
            dir=self.last_save_dir,
            filter='H5AD (*.h5ad)',
        )
        if not file_path:
            return

        temp_data = painter.data.copy()
        temp_data.layers.clear()
        temp_data.write(filename=file_path, compression='gzip')

        self.last_save_dir = str(Path(file_path).parent)

    def load_layout(self) -> LayoutConfig:
        file_path, _ = QFileDialog.getOpenFileName(
            None, 'Load Layout', str(layout_dir), 'YAML (*.yml)'
        )
        if not file_path:
            return

        return LayoutConfig.from_yaml(file_path)

    def save_layout(self, painter: Painter) -> None:
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
                painter.layout_to_yaml(),
                f,
                default_flow_style=None,
                sort_keys=False,
                explicit_start=True,
            )


def open_fcs(file: Path) -> Painter:
    fcs = flowio.FlowData(file)
    return Painter.from_fcs(fcs)


def open_session(file: Path) -> Painter:
    adata = ad.io.read_h5ad(file)
    return Painter.from_adata(adata)


def get_child_files(dir: Path) -> list[Path]:
    return list(filter(_is_valid_file, dir.iterdir()))


def _is_valid_filetype(path: Path) -> bool:
    return path.suffix.lower() in ['.fcs', '.h5ad']


def _is_valid_file(path: Path) -> bool:
    return path.is_file() and _is_valid_filetype(path)


def filter_valid_files(files: Iterable[Path]) -> list[Path]:
    return list(filter(_is_valid_file, files))


def get_files_from_urls(urls: list[QUrl]) -> list[Path]:
    def _expand_url(url: QUrl) -> Iterable[Path]:
        path = Path(url.toLocalFile())
        if path.is_dir():
            return get_child_files(path)
        elif _is_valid_file(path):
            return [path]
        else:
            return []

    return list(chain(*map(_expand_url, urls)))


def _scrub_metadata(metadata: dict[str, str]) -> dict[str, str]:
    return {
        k: v
        for k, v in metadata.items()
        if k
        in flowio.fcs_keywords.FCS_STANDARD_REQUIRED_KEYWORDS + ['spill', 'spillover']
    }
