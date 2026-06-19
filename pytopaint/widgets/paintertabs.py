from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QTabWidget

from pytopaint.widgets.painter import Painter


class PainterTabs(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setElideMode(Qt.TextElideMode.ElideMiddle)
        self.tabCloseRequested.connect(self.handle_tab_close)
        self.setMinimumSize(600, 400)

    @Slot(int)
    def handle_tab_close(self, index: int):
        widget = self.widget(index)
        self.removeTab(index)
        if widget is not None:
            widget.deleteLater()

    def close_all_tabs(self):
        while self.count() > 0:
            self.handle_tab_close(0)

    def add_painter(self, painter: Painter):
        self.addTab(painter, painter.data.name)
        self.setCurrentWidget(painter)

    def sizeHint(self):
        current = self.currentWidget()
        if not current:
            return super().sizeHint()
        return current.sizeHint()

    def minimumSizeHint(self):
        current = self.currentWidget()
        if not current:
            return super().minimumSizeHint()
        return current.minimumSizeHint()
