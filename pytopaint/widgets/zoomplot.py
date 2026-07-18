# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

from PySide6.QtCore import Signal
from PySide6.QtGui import (
    QKeySequence,
    QShortcut,
)
from PySide6.QtWidgets import QDialog, QLayout, QVBoxLayout

from pytopaint.colors import Color
from pytopaint.shortcuts import configure_paint_shortcuts
from pytopaint.widgets.biplot import Biplot


class ZoomPlot(QDialog):
    menuActionTriggered = Signal(int, dict)

    def __init__(self, biplot: Biplot, parent=None):
        super().__init__(parent)
        self.active_color = biplot.active_color
        layout = QVBoxLayout()

        layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        layout.addWidget(biplot)
        self.setLayout(layout)

        close_shortcut = QShortcut(QKeySequence('Space'), self)
        biplot.menuActionTriggered.connect(lambda: close_shortcut.setEnabled(False))
        biplot.updateFinished.connect(lambda: close_shortcut.setEnabled(True))
        close_shortcut.activated.connect(self.accept)
        biplot.activeColorChanged.connect(self.update_active_color)

        configure_paint_shortcuts(self)

    def update_active_color(self, color: Color) -> None:
        self.active_color = color
