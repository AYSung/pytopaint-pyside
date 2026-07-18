from PySide6.QtCore import Signal
from PySide6.QtGui import (
    QKeySequence,
    QShortcut,
)
from PySide6.QtWidgets import QDialog, QLayout, QVBoxLayout

from pytopaint.shortcuts import configure_paint_shortcuts
from pytopaint.widgets.biplot import Biplot


class ZoomPlot(QDialog):
    menuActionTriggered = Signal(int, dict)

    def __init__(self, biplot: Biplot, parent=None):

        super().__init__(parent)
        layout = QVBoxLayout()

        layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        layout.addWidget(biplot)
        self.setLayout(layout)

        close_shortcut = QShortcut(QKeySequence('Space'), self)
        biplot.menuActionTriggered.connect(lambda: close_shortcut.setEnabled(False))
        biplot.updateFinished.connect(lambda: close_shortcut.setEnabled(True))
        close_shortcut.activated.connect(self.accept)

        configure_paint_shortcuts(self)
