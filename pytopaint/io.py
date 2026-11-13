# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

from collections.abc import Iterable
from itertools import chain
from pathlib import Path

import anndata as ad
import polars as pl

# import flowio
import yaml
from pyreflow import CoreDataset3_0, CoreDataset3_1
from pyreflow.api import fcs_read_header, fcs_read_std_dataset
from pyreflow.typing import AnyCoreDataset
from PySide6.QtCore import QDir, QObject, QUrl, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QProgressDialog,
)

from pytopaint.config import get_painter_layout_directory
from pytopaint.flowdata import FlowData
from pytopaint.layout import LayoutConfig
from pytopaint.reporting import generate_pdf
from pytopaint.widgets.dialogs import TubeSelector
from pytopaint.widgets.painter import Painter


class IOManager(QObject):
    fileOpened = Signal(object)
    finished = Signal(bool)

    last_file_dir: str
    last_file_parent_dir: str
    last_case_dir: str
    last_case_parent_dir: str
    last_save_dir: str

    def __init__(self, parent=None):
        super().__init__(parent)
        self.last_file_dir = QDir.homePath()
        self.last_file_parent_dir = QDir.homePath()
        self.reset_case_dir()
        self.last_save_dir = QDir.homePath()
        self.file_parsers = {'.fcs': open_fcs, '.h5ad': open_session}

    @Slot()
    def reset_case_dir(self):
        self.last_case_dir = QDir.homePath()
        self.last_case_parent_dir = QDir.homePath()

    def open_files(self, files: list[Path]) -> None:
        progress = QProgressDialog(
            'Opening files...', 'Cancel', 0, len(files), self.parent()
        )

        progress.open()
        self.finished.emit(False)
        for i, file in enumerate(files, start=1):
            if progress.wasCanceled():
                break

            try:
                painter = self.file_parsers[file.suffix.lower()](file)
                self.fileOpened.emit(painter)
            except ValueError as e:
                print(f'Error opening {file}')
                print(e)
            finally:
                progress.setValue(i)
                QApplication.processEvents()

        self.finished.emit(True)

    @Slot()
    def open_files_dialog(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            None,
            'Select File(s)',
            self.last_file_dir,
            'Flow Data (*.fcs *.h5ad)',
        )

        paths = filter_valid_files(map(Path, files))
        if not paths:
            return

        self.open_files(paths)
        self.last_file_dir = str(paths[-1].parent)

    @Slot()
    def open_dir_dialog(self) -> None:
        dir = QFileDialog.getExistingDirectory(
            None,
            'Select Directory',
            self.last_file_parent_dir,
            QFileDialog.Option.ShowDirsOnly,
        )
        dir = Path(dir)
        files = get_child_files(dir)
        if not files:
            return

        self.open_files(files)
        self.last_file_dir = str(dir)
        self.last_file_parent_dir = str(dir.parent)

    @Slot()
    def open_case_dialog(self) -> None:
        dir = QFileDialog.getExistingDirectory(
            None,
            'Select Case Directory',
            self.last_case_parent_dir,
            QFileDialog.Option.ShowDirsOnly,
        )
        dir = Path(dir)
        files = get_child_files(dir)
        if not files:
            return

        self.open_files(files)
        self.last_case_dir = str(dir)
        self.last_case_parent_dir = str(dir.parent)

    def open_files_from_urls(self, urls: list[QUrl]) -> None:
        paths = get_files_from_urls(urls)
        if paths:
            self.open_files(paths)
            self.last_file_dir = str(paths[-1].parent)

    @Slot()
    def export_fcs(self, painter: Painter) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            parent=None,
            caption='Export Deidentified FCS',
            dir=self.last_save_dir,
            filter='FCS (*.fcs)',
        )
        if not file_path:
            return

        fcs = painter.data.fcs
        event_mask = painter.state['visible']
        fcs.data = fcs.data.filter(pl.Series(painter.state['visible']))
        # TODO: switch to color == -2

        export_fcs(fcs, file_path)

        self.last_save_dir = str(Path(file_path).parent)

    @Slot()
    def save_session(self, painter: Painter) -> None:
        painter.update_flowdata_state()

        file_path, _ = QFileDialog.getSaveFileName(
            parent=None,
            caption='Save Session',
            dir=self.last_save_dir,
            filter='H5AD (*.h5ad)',
        )
        if not file_path:
            return

        temp_data = painter.data.adata.copy()
        temp_data.layers.clear()
        temp_data.write(filename=file_path, compression='gzip')

        self.last_save_dir = str(Path(file_path).parent)

    @Slot()
    def load_layout(self) -> LayoutConfig:
        file_path, _ = QFileDialog.getOpenFileName(
            None, 'Load Layout', str(get_painter_layout_directory()), 'YAML (*.yml)'
        )
        if not file_path:
            return

        return LayoutConfig.from_yaml(file_path)

    def save_layout(self, painter: Painter) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            parent=None,
            caption='Save Layout',
            dir=str(get_painter_layout_directory()),
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

    def export_to_pdf(self, tubes: list[Painter], parent=None) -> None:
        if len(tubes) > 1:
            dialog = TubeSelector(
                tubes,
                'Select Tubes',
                parent,
            )

            if dialog.exec() == QDialog.DialogCode.Accepted:
                tubes = dialog.selected_tubes
            else:
                return

        case_numbers = {tube.data.case_id for tube in tubes}
        default_export_name = case_numbers.pop() if len(case_numbers) == 1 else ''
        export_dir = (
            self.last_case_dir
            if self.last_case_dir != QDir.homePath()
            else self.last_file_dir
        )

        file_path, _ = QFileDialog.getSaveFileName(
            parent=None,
            caption='Export PDF Report',
            dir=export_dir + f'/{default_export_name}',
            filter='PDF (*.pdf)',
        )

        if not file_path:
            return

        generate_pdf(file_path, tubes)


def open_fcs(file: Path) -> Painter:
    data = read_fcs(file)
    return Painter(data)


def open_session(file: Path) -> Painter:
    adata = ad.io.read_h5ad(file)
    return Painter.from_adata(adata)


def get_child_files(dir: Path) -> list[Path]:
    return list(
        filter(_is_not_blank_or_viability, filter(_is_valid_file, dir.iterdir()))
    )


def _is_not_blank_or_viability(path: Path) -> bool:
    return (
        'blank' not in path.stem.lower()
        and 'viability' not in path.stem.lower()
        and 'cell count' not in path.stem.lower()
    )


def _is_valid_filetype(path: Path) -> bool:
    return path.suffix.lower() in ['.fcs', '.h5ad']


def _is_valid_file(path: Path) -> bool:
    return path.is_file() and _is_valid_filetype(path) and not path.stem.startswith('.')


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


def get_fcs_version(filepath: Path) -> str:
    return fcs_read_header(filepath).version


def read_fcs(filepath: Path) -> FlowData:
    fcs_version = get_fcs_version(filepath)
    match fcs_version:
        case 'FCS3.0':
            dataset = _read_fcs_3_0(filepath)
        case 'FCS3.1':
            dataset = _read_fcs_3_1(filepath)
        case 'FCS3.2':
            dataset = _read_fcs_3_1(filepath)
        case _:
            raise NotImplementedError
            # dataset = fcs_read_std_dataset(filepath)

    return FlowData.from_fcs(dataset)


def _read_fcs_3_0(filepath: Path) -> CoreDataset3_0:
    dataset, _ = fcs_read_std_dataset(
        filepath,
        ignore_optical_only_keys=['G'],
        add_missing_timestep=True,
        allow_missing_crc='true',
    )
    return dataset


def _read_fcs_3_1(filepath: Path) -> CoreDataset3_1:
    dataset, _ = fcs_read_std_dataset(
        filepath,
        trim_value_whitespace='trim',
        allow_missing_crc='true',
        version_override='loose',
    )
    return dataset


def export_fcs(dataset: AnyCoreDataset, filepath: Path) -> None:
    dataset.src = 'DEIDENTIFIED'
    dataset.fil = 'DEIDENTIFIED'
    dataset.sys = 'DEIDENTIFIED'
    dataset.cyt = 'DEIDENTIFIED'
    dataset.cytsn = 'DEIDENTIFIED'
    dataset.op = 'DEIDENTIFIED'
    dataset.proj = 'DEIDENTIFIED'
    dataset.smno = 'DEIDENTIFIED'
    dataset.inst = 'DEIDENTIFIED'
    dataset.date = None
    dataset.btim = None
    dataset.etim = None

    if dataset.version == 'FCS3.0':
        dataset.nonstandard_keywords = {
            k: v
            for k, v in dataset.nonstandard_keywords.items()
            if k.lower() in ['spill']
        }

    elif dataset.version in ['FCS3.1', 'FCS3.2']:
        dataset.begindatetime = None
        dataset.enddatetime = None
        dataset.carriertype = 'DEIDENTIFIED'
        dataset.carrierid = 'DEIDENTIFIED'
        dataset.platename = 'DEIDENTIFIED'
        dataset.plateid = 'DEIDENTIFIED'
        dataset.wellid = 'DEIDENTIFIED'
        dataset.locationid = 'DEIDENTIFIED'
        dataset.nonstandard_keywords = {}

    dataset.write_dataset(filepath, compute_crc=True, override_fil=True)
