# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.


from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QTabWidget

from pytopaint.widgets.painter import Painter


class PainterTabs(QTabWidget):
    resizeTriggered = Signal()
    rescaleTriggered = Signal(object)
    colorPaletteChanged = Signal()
    zoomUpdated = Signal()
    allTabsClosed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setElideMode(Qt.TextElideMode.ElideMiddle)
        self.tabCloseRequested.connect(self.handle_tab_close)
        self.setStyleSheet(
            'QTabWidget::pane {background-color: #333333; border: 1px solid #444444; border-radius: 5px;}'
        )

    @Slot(int)
    def handle_tab_close(self, index: int):
        widget = self.widget(index)
        self.removeTab(index)
        if widget is not None:
            widget.deleteLater()

        if self.count() == 0:
            self.allTabsClosed.emit()

    @Slot(object)
    def handle_rescale(self, scale_config: dict[str, float]) -> None:
        widget: Painter = self.currentWidget()
        if widget:
            widget.handle_rescale(scale_config)

    @Slot()
    def close_all_tabs(self):
        while self.count() > 0:
            self.handle_tab_close(0)

    @Slot(object)
    def add_painters(self, painters: list[Painter]):
        for painter in sort_painters(painters):
            self.add_painter(painter)
        self.setCurrentIndex(self.count() - len(painters))

    def add_painter(self, painter: Painter):
        self.resizeTriggered.connect(painter.handle_resize)
        self.rescaleTriggered.connect(painter.handle_rescale)
        self.colorPaletteChanged.connect(painter.colorPaletteChanged)
        self.zoomUpdated.connect(painter.change_zoom)
        self.addTab(painter, painter.data.id)
        self.setCurrentWidget(painter)

    @property
    def painters(self) -> list[Painter]:
        return [self.widget(i) for i in range(self.count())]

    def paintEvent(self, event):
        super().paintEvent(event)

        if not self.count():
            painter = QPainter(self)
            painter.setPen('#bababa')

            text = 'Welcome to PytoPaint!\n\nOpen files / directories by dragging and dropping into this window or via the File menu'

            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)


def sort_painters(painters: list[Painter]):
    TUBE_ORDER = [
        'B CELL',
        'T CELL',
        'BMS',
        'AML-MDS',
        'MMIC',
        'VS38C',
        'BLL-REFLEX MRD TUBE',
        'CART-19 TUBE 3',
        'CART-19 TUBE 4',
        'T-ALL REFLEX TUBE',
        'BM T-LL REFLEX TUBE',
        'MPO TUBE',
        'MPO ISO',
        'TDT TUBE',
        'TDT ISO',
        'CLL REFLEX TUBE',
        'HC REFLEX TUBE',
        'MYCOSIS TUBE',
        'HES TUBE',
    ]
    SORT_KEYS = {k: i for i, k in enumerate(TUBE_ORDER)}
    return sorted(
        painters, key=lambda x: SORT_KEYS.get(x.data.tube.upper(), float('inf'))
    )
