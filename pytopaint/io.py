from collections.abc import Iterable
from itertools import chain
from pathlib import Path

import anndata as ad
import flowio
from PySide6.QtCore import (
    QCoreApplication,
    QDir,
    QObject,
    Qt,
    QThread,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QProgressDialog,
)

from pytopaint.widgets.painter import Painter


class IOManager(QObject):
    fileOpened = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.last_dir = QDir.homePath()
        self.file_parsers = {'.fcs': open_fcs, '.h5ad': open_session}

    def open_files(self, files: list[Path]) -> None:
        progress = QProgressDialog(
            'Opening files...', 'Cancel', 0, len(files), self.parent()
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)

        progress.show()
        for i, file in enumerate(files, start=1):
            if progress.wasCanceled():
                break
            painter = self.file_parsers[file.suffix.lower()](file)
            progress.setValue(i)
            QApplication.processEvents()
            self.fileOpened.emit(painter)
            self.last_dir = str(file.parent)

    @Slot()
    def open_files_dialog(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            None, 'Select File(s)', self.last_dir, 'FCS (*.fcs);;H5AD (*.h5ad)'
        )
        paths = filter_valid_files(map(Path, files))
        self.open_files(paths)

    @Slot()
    def open_dir_dialog(self) -> None:
        dir = QFileDialog.getExistingDirectory(
            None, 'Select Directory', self.last_dir, QFileDialog.Option.ShowDirsOnly
        )
        self.open_files(get_child_files(dir))

    def open_files_from_urls(self, urls: list[QUrl]) -> None:
        paths = get_files_from_urls(urls)
        self.open_files(paths)


def open_fcs(file: Path) -> Painter:
    try:
        fcs = flowio.FlowData(file)
        return Painter.from_fcs(fcs)

    except ValueError as e:
        raise e


def open_session(file: Path) -> Painter:
    try:
        adata = ad.io.read_h5ad(file)
        return Painter.from_adata(adata)

    except ValueError as e:
        raise e


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
