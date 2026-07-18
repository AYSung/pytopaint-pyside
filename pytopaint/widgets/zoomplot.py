from PySide6.QtCore import Signal
from PySide6.QtGui import (
    QKeySequence,
    QShortcut,
)
from PySide6.QtWidgets import QDialog, QLayout, QVBoxLayout

from pytopaint.actions import MenuAction
from pytopaint.colors import COLOR_SHORTCUTS, Color
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

        def _color_shortcut(key: str, color: Color) -> QShortcut:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(
                lambda: self.menuActionTriggered.emit(
                    MenuAction.SET_ACTIVE, dict(color=color)
                )
            )

        for key, color in COLOR_SHORTCUTS:
            _color_shortcut(key, color)
