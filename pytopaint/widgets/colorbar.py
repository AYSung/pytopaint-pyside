from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QWidget,
    QMenu,
    QStyle,
    QStyleOption,
)
from PySide6.QtGui import QMouseEvent, QAction, QPixmap, QIcon, QPainter
from PySide6.QtCore import Slot, Qt, Signal

import pandas as pd

from pytopaint.colors import (
    Color,
    COLOR_RGB_MAP,
    COLOR_NAME_MAP,
    events_by_colors,
    ratios_by_color,
)
from pytopaint.actions import MenuAction

RESOLUTION = 256


class ColorBar(QWidget):
    activeColorChanged = Signal(int)
    menuActionTriggered = Signal(int, dict)
    eventsUpdated = Signal(object, int)
    highlightsUpdated = Signal(list)

    def __init__(self):
        super().__init__()

        layout = QHBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(20, 0, 0, 0)

        self.total_events_label = QLabel()
        self.total_events_label.setFixedWidth(150)
        layout.addWidget(self.total_events_label)

        self.color_labels = [ColorLabel(c) for c in COLOR_RGB_MAP.keys()]
        for color_label in self.color_labels:
            layout.addWidget(color_label)
            color_label.menuActionTriggered.connect(self.menuActionTriggered)
            self.highlightsUpdated.connect(color_label.update_highlight)
            self.activeColorChanged.connect(color_label.update_active_color)
            self.eventsUpdated.connect(color_label.update_label)

        layout.addStretch()

        self.setLayout(layout)

    @Slot(object)
    def update_labels(self, df: pd.DataFrame):
        events, total_events = events_by_colors(df)
        self.eventsUpdated.emit(events, total_events)
        self.total_events_label.setText(f'Total Events: {total_events:,}')

    def paintEvent(self, pe):
        o = QStyleOption()
        o.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, o, p, self)


class ColorLabel(QWidget):
    menuActionTriggered = Signal(int, dict)

    def __init__(self, color: Color, parent=None):
        super().__init__(parent)
        self.color = color
        self.highlight = False
        self.events = 0

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)
        self.setFixedWidth(150)

        layout = QHBoxLayout()

        self.box = QLabel()
        self.box.setFixedSize(12, 12)
        self.box.setStyleSheet(f'background-color: {COLOR_RGB_MAP[color]}')

        self.label = QLabel()

        layout.addWidget(self.box)
        layout.addWidget(self.label)

        self.setLayout(layout)

    @Slot(object, int)
    def update_label(self, events: dict[Color, int], total_events: int):
        self.events = events.get(self.color, 0)
        self.ratios = ratios_by_color(self.color, events)
        percent = self.events / total_events
        decimal_places = 1 if (percent == 0) or (percent >= 0.01) else 2
        if (self.events >= 100) or (self.events == 0):
            self.label.setText(f'{percent:.{decimal_places}%}')
        else:
            self.label.setText(f'{percent:.{decimal_places}%} ({self.events})')

    def mouseReleaseEvent(self, e: QMouseEvent):
        modifiers = e.modifiers()
        if e.button() == Qt.MouseButton.LeftButton:
            if modifiers == Qt.KeyboardModifier.NoModifier:
                self.menuActionTriggered.emit(
                    MenuAction.SET_ACTIVE, dict(color=self.color)
                )
            elif modifiers == Qt.KeyboardModifier.ShiftModifier:
                self.menuActionTriggered.emit(
                    MenuAction.HIGHLIGHT, dict(color=self.color)
                )
        elif (self.events > 0) and e.button() == Qt.MouseButton.MiddleButton:
            if modifiers == Qt.KeyboardModifier.NoModifier:
                self.menuActionTriggered.emit(
                    MenuAction.EXACT_ZAP, dict(color=self.color)
                )
            # elif modifiers == Qt.KeyboardModifier.ShiftModifier:
            #     self.menuActionTriggered.emit(MenuAction.ZAP, dict(color=self.color))

    @Slot(list)
    def update_highlight(self, highlighted_colors: list[Color]):
        self.highlight = self.color in highlighted_colors
        if self.highlight:
            self.box.setFixedSize(16, 16)
        else:
            self.box.setFixedSize(12, 12)

    @Slot(int)
    def update_active_color(self, color: Color):
        self.label.setStyleSheet(
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
        if self.color != Color.GREY:
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
        self.toggle_highlight.triggered.connect(
            lambda: self.menuActionTriggered.emit(
                MenuAction.HIGHLIGHT, dict(color=self.color)
            )
        )
        menu.addAction(self.toggle_highlight)

        if self.color != Color.GREY:
            menu.addSeparator()

            zap = QAction('Zap', enabled=self.events > 0)
            zap.triggered.connect(
                lambda: self.menuActionTriggered.emit(
                    MenuAction.ZAP, dict(color=self.color)
                )
            )
            menu.addAction(zap)

            exact_zap = QAction('Exact Zap', enabled=self.events > 0)
            exact_zap.triggered.connect(
                lambda: self.menuActionTriggered.emit(
                    MenuAction.EXACT_ZAP, dict(color=self.color)
                )
            )
            menu.addAction(exact_zap)

            merge_menu = QMenu('Merge with...')
            merge_menu.setEnabled(self.events > 0)

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
        hide = QAction('Hide Color', enabled=self.events > 0)
        hide.triggered.connect(
            lambda: self.menuActionTriggered.emit(
                MenuAction.HIDE, dict(color=self.color)
            )
        )
        menu.addAction(hide)
        isolate = QAction('Isolate Color', enabled=self.events > 0)
        isolate.triggered.connect(
            lambda: self.menuActionTriggered.emit(
                MenuAction.ISOLATE, dict(color=self.color)
            )
        )
        menu.addAction(isolate)

        menu.addSection('Ratios')

        ratio_labels = [
            QAction(
                f'{ratio:.{1 if ratio >= 1 else 2}f} : 1 {COLOR_NAME_MAP[color]}',
                enabled=False,
            )
            for color, ratio in self.ratios.items()
            if ratio
        ]
        for label in ratio_labels:
            menu.addAction(label)

        menu.exec(self.mapToGlobal(pos))
