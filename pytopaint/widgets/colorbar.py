from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QWidget,
    QMenu,
)
from PySide6.QtGui import QMouseEvent, QAction, QPixmap, QIcon
from PySide6.QtCore import Slot, Qt, Signal

# import polars as pl
from pytopaint.colors import (
    Color,
    COLOR_RGB_MAP,
    COLOR_NAME_MAP,
)
from pytopaint.actions import MenuAction

RESOLUTION = 256


class ColorLabel(QWidget):
    highlight_color = Signal(int, bool)
    menuActionTriggered = Signal(int, dict)

    def __init__(self, color: Color, parent=None):
        super().__init__(parent)
        self.color = color
        self.highlight = False
        self.percent = 0

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

        layout = QHBoxLayout()

        self.box = QLabel()
        self.box.setFixedSize(12, 12)
        self.box.setStyleSheet(f'background-color: {COLOR_RGB_MAP[color]}')

        self.percent_label = QLabel()

        layout.addWidget(self.box)
        layout.addWidget(self.percent_label)

        self.setLayout(layout)

    @Slot(object)
    def update_percent(self, percents: dict[Color:float]):
        self.percent = percents.get(self.color, 0)
        decimal_places = 1 if (self.percent == 0) or (self.percent >= 0.01) else 2
        self.percent_label.setText(f'{self.percent:.{decimal_places}%}')

    def mouseReleaseEvent(self, e: QMouseEvent):
        if e.button() == Qt.MouseButton.LeftButton:
            self.emit_highlight()
        # elif e.button() == Qt.MouseButton.RightButton:
        #     ...  # hide color

    def emit_highlight(self):
        self.highlight = not self.highlight
        self.highlight_color.emit(self.color, self.highlight)
        if self.highlight:
            self.box.setFixedSize(16, 16)
        else:
            self.box.setFixedSize(12, 12)

    @Slot(int)
    def update_active_color(self, color: Color):
        self.percent_label.setStyleSheet(
            f'font-weight: {"bold" if self.color == color else "normal"};'
        )

    def context_menu(self, pos):
        def _merge_action(color: Color, name: str) -> QAction:
            def _color_icon(color: Color) -> QIcon:
                pixmap = QPixmap(12, 12)
                pixmap.fill(COLOR_RGB_MAP[color])
                return QIcon(pixmap)

            action = QAction(_color_icon(color), name)
            action.triggered.connect(
                lambda: self.menuActionTriggered.emit(
                    MenuAction.MERGE, dict(source_color=self.color, target_color=color)
                )
            )
            return action

        menu = QMenu()
        # set active color
        if self.color in [Color.RED, Color.BLUE, Color.GREEN]:
            set_active_color = QAction('Set Active Color')
            set_active_color.triggered.connect(
                lambda: self.menuActionTriggered.emit(
                    MenuAction.SET_ACTIVE, dict(color=self.color)
                )
            )
            menu.addAction(set_active_color)

        # highlight points
        self.toggle_highlight = QAction('Highlight')
        self.toggle_highlight.setCheckable(True)
        self.toggle_highlight.setChecked(self.highlight)
        self.toggle_highlight.triggered.connect(self.emit_highlight)
        menu.addAction(self.toggle_highlight)

        if self.color != Color.GREY:
            zap = QAction('Zap', enabled=self.percent > 0)
            zap.triggered.connect(
                lambda: self.menuActionTriggered.emit(
                    MenuAction.ZAP, dict(color=self.color)
                )
            )
            menu.addAction(zap)

            exact_zap = QAction('Exact Zap', enabled=self.percent > 0)
            exact_zap.triggered.connect(
                lambda: self.menuActionTriggered.emit(
                    MenuAction.EXACT_ZAP, dict(color=self.color)
                )
            )
            menu.addAction(exact_zap)

            menu.addSeparator()
            merge_menu = QMenu('Merge with...')
            merge_menu.setEnabled(self.percent > 0)

            merge_actions = [
                _merge_action(color, name)
                for color, name in COLOR_NAME_MAP.items()
                if color != self.color
            ]

            for merge_action in merge_actions:
                merge_menu.addAction(merge_action)
            menu.addMenu(merge_menu)

        menu.addSeparator()
        menu.addSection('Filter')
        hide = QAction('Hide Color', enabled=self.percent > 0)
        hide.triggered.connect(
            lambda: self.menuActionTriggered.emit(
                MenuAction.HIDE, dict(color=self.color)
            )
        )
        menu.addAction(hide)
        isolate = QAction('Isolate Color', enabled=self.percent > 0)
        isolate.triggered.connect(
            lambda: self.menuActionTriggered.emit(
                MenuAction.ISOLATE, dict(color=self.color)
            )
        )
        menu.addAction(isolate)

        menu.exec(self.mapToGlobal(pos))


class ColorBar(QWidget):
    highlight_color = Signal(int, bool)
    activeColorChanged = Signal(int)
    menuActionTriggered = Signal(int, dict)

    def __init__(self):
        super().__init__()

        layout = QHBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        self.color_labels = [ColorLabel(c) for c in COLOR_RGB_MAP.keys()]
        for color_label in self.color_labels:
            layout.addWidget(color_label)
            color_label.menuActionTriggered.connect(self.menuActionTriggered)
            # color_label.set_active_color.connect(self.set_active_color)
            color_label.highlight_color.connect(self.highlight_color)
            # color_label.zap_color.connect(self.zap_color)
            # color_label.exact_zap_color.connect(self.exact_zap_color)
            # color_label.hide_color.connect(self.hide_color)
            # color_label.isolate_color.connect(self.isolate_color)
            self.activeColorChanged.connect(color_label.update_active_color)

        self.setLayout(layout)

    @Slot(object)
    def update_percent(self, percents: dict[Color, float]):
        for color_label in self.color_labels:
            color_label.update_percent(percents)
