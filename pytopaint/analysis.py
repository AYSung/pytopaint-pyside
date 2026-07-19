# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

from typing import Callable

import numpy as np
from PySide6.QtCore import QObject, QRunnable, Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QProgressDialog
from sklearn.preprocessing import RobustScaler
from umap import UMAP


def umap_transform(arr: np.ndarray) -> np.ndarray:
    scaled_arr = RobustScaler().fit_transform(arr)
    umap = UMAP(init='pca', verbose=True, min_dist=0.4, n_neighbors=15, random_state=42)
    rng = np.random.default_rng(seed=42)
    umap.fit(rng.choice(scaled_arr, size=min(20_000, arr.shape[0]), replace=False))
    return umap.transform(scaled_arr)


class WorkerSignal(QObject):
    analysisFinished = Signal(object)


class AnalysisWorker(QRunnable):
    def __init__(self, arr: np.ndarray, func: Callable):
        super().__init__()
        self.signals = WorkerSignal()
        self.arr = arr
        self.func = func

    def run(self) -> None:
        result = self.func(self.arr)
        self.signals.analysisFinished.emit(result)


def umap_worker(arr: np.ndarray) -> AnalysisWorker:
    return AnalysisWorker(arr=arr, func=umap_transform)


class AnalysisProgressDialog(QProgressDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCancelButton(None)

    def keyPressEvent(self, e: QKeyEvent):
        if e.key() == Qt.Key.Key_Escape:
            e.ignore()
        else:
            super().keyPressEvent(e)
