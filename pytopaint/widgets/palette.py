import pandas as pd
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QAction, QIcon, QMouseEvent, QPainter, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QStyle,
    QStyleOption,
    QWidget,
    QToolButton,
)

from pytopaint.actions import MenuAction
from pytopaint.colors import (
    COLOR_RGB_MAP,
    Color,
    events_by_color,
    ratios_by_color,
    is_zappable,
)


class Palette(QWidget):
    activeColorChanged = Signal(int)
    menuActionTriggered = Signal(int, dict)
    eventsUpdated = Signal(object, int)
    highlightsUpdated = Signal(list)

    def __init__(self, memory_states: int):
        super().__init__()

        layout = QHBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(20, 0, 20, 0)

        self.total_events_label = QLabel()
        self.total_events_label.setFixedWidth(150)
        layout.addWidget(self.total_events_label)

        self.color_labels = [ColorLabel(c) for c in Color]
        for color_label in self.color_labels:
            layout.addWidget(color_label)
            color_label.menuActionTriggered.connect(self.menuActionTriggered)
            self.highlightsUpdated.connect(color_label.update_highlight)
            self.activeColorChanged.connect(color_label.update_active_color)
            self.eventsUpdated.connect(color_label.update_label)

        save_state_label = QLabel('Snapshots:')
        save_state_label.setContentsMargins(0, 0, 10, 0)
        layout.addWidget(save_state_label)
        self.memory_slots = {i: MemorySlot(i) for i in range(memory_states)}
        for memory_slot in self.memory_slots.values():
            layout.addWidget(memory_slot)
            memory_slot.menuActionTriggered.connect(self.menuActionTriggered)

        layout.addStretch()

        self.setLayout(layout)

    @Slot(object)
    def update_labels(self, df: pd.DataFrame):
        events = events_by_color(df.color)
        total_events = df.color.size
        self.total_events_label.setText(f'Total Events: {total_events:,}')

        self.eventsUpdated.emit(events, total_events)

    def paintEvent(self, _: QStyle.PrimitiveElement):
        o = QStyleOption()
        o.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, o, p, self)


class ColorLabel(QWidget):
    menuActionTriggered = Signal(int, dict)

    def __init__(self, color: Color, parent=None):
        super().__init__(parent)
        self.color = color
        self.highlight = False
        self.event_count = 0
        self.zappable = False

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

    @property
    def has_events(self) -> bool:
        return self.event_count > 0

    @Slot(object, int)
    def update_label(self, events: dict[Color, int], total_events: int):
        self.event_count = events.get(self.color, 0)
        percent = self.event_count / total_events
        if (self.event_count >= 100) or (self.event_count == 0):
            self.label.setText(_format_percent(percent))
        else:
            self.label.setText(f'{_format_percent(percent)} ({self.event_count})')

        self.zappable = is_zappable(self.color, events)
        self.ratios = ratios_by_color(
            self.color,
            {color: n / total_events for color, n in sorted(events.items())},
        )

    def mouseReleaseEvent(self, e: QMouseEvent):
        if self.color == Color.GREY:
            return

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
        elif self.has_events and (e.button() == Qt.MouseButton.MiddleButton):
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
        def _merge_action(color: Color) -> QAction:
            action = QAction(_color_icon(color), color.label_name)
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
            self.toggle_highlight = QAction(
                'Highlight', checkable=True, checked=self.highlight
            )
            self.toggle_highlight.triggered.connect(
                lambda: self.menuActionTriggered.emit(
                    MenuAction.HIGHLIGHT, dict(color=self.color)
                )
            )
            menu.addAction(self.toggle_highlight)

            menu.addSeparator()

            zap = QAction('Zap', enabled=self.zappable)
            zap.triggered.connect(
                lambda: self.menuActionTriggered.emit(
                    MenuAction.ZAP, dict(color=self.color)
                )
            )
            menu.addAction(zap)

            exact_zap = QAction('Exact Zap', enabled=self.has_events)
            exact_zap.triggered.connect(
                lambda: self.menuActionTriggered.emit(
                    MenuAction.EXACT_ZAP, dict(color=self.color)
                )
            )
            menu.addAction(exact_zap)

            merge_menu = QMenu('Merge with...')
            merge_menu.setEnabled(self.has_events)

            merge_actions = [
                _merge_action(color) for color in Color if color != self.color
            ]

            for merge_action in merge_actions:
                merge_menu.addAction(merge_action)
            menu.addMenu(merge_menu)

        menu.addSeparator()
        menu.addSection('Filter')
        hide = QAction('Hide Color', enabled=self.has_events)
        hide.triggered.connect(
            lambda: self.menuActionTriggered.emit(
                MenuAction.HIDE, dict(color=self.color)
            )
        )
        menu.addAction(hide)
        isolate = QAction('Isolate Color', enabled=self.has_events)
        isolate.triggered.connect(
            lambda: self.menuActionTriggered.emit(
                MenuAction.ISOLATE, dict(color=self.color)
            )
        )
        menu.addAction(isolate)

        menu.addSection('Ratios')

        ratio_labels = [
            QAction(
                _color_icon(color),
                f'{_format_ratio(label_info[0])} ({_format_percent(label_info[1])})',
                enabled=False,
            )
            for color, label_info in self.ratios.items()
        ]
        menu.addActions(ratio_labels)

        menu.exec(self.mapToGlobal(pos))


def _format_percent(percent: float) -> int:
    return f'{percent:.{1 if (percent == 0) or (percent >= 0.01) else 2}%}'


def _format_ratio(ratio: float) -> int:
    return f'{ratio:.{1 if ratio >= 1 else 2}f} : 1'


def _color_icon(color: Color) -> QIcon:
    pixmap = QPixmap(16, 12)
    pixmap.fill('#00000000')
    painter = QPainter(pixmap)
    painter.fillRect(0, 0, 12, 12, COLOR_RGB_MAP[color])
    painter.end()
    return QIcon(pixmap)


class MemorySlot(QToolButton):
    menuActionTriggered = Signal(int, dict)

    def __init__(self, id: int, parent=None):
        super().__init__(parent)
        self.id = id
        self.setText(str(id))
        self.has_events = False
        self.update_appearance()
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

    def mouseReleaseEvent(self, e: QMouseEvent):
        modifiers = e.modifiers()
        if e.button() == Qt.MouseButton.LeftButton:
            if modifiers == Qt.KeyboardModifier.NoModifier:
                self.recall_state()
            elif modifiers == Qt.KeyboardModifier.ShiftModifier:
                self.combine_state()
        elif e.button() == Qt.MouseButton.MiddleButton:
            if modifiers == Qt.KeyboardModifier.NoModifier:
                self.clear_state()

        super().mouseReleaseEvent(e)

    def update_appearance(self) -> None:
        self.setStyleSheet(
            f'background-color: {"#828282" if self.has_events else "#121212"}'
        )

    def context_menu(self, pos):
        menu = QMenu()
        recall_state_action = QAction('Recall', self, enabled=self.has_events)
        recall_state_action.triggered.connect(self.recall_state)
        menu.addAction(recall_state_action)
        combine_state_action = QAction('Combine', self, enabled=self.has_events)
        combine_state_action.triggered.connect(self.combine_state)
        menu.addAction(combine_state_action)

        menu.addSeparator()

        store_state_action = QAction('Store', self)
        store_state_action.triggered.connect(self.store_state)
        menu.addAction(store_state_action)
        clear_state_action = QAction('Clear', self, enabled=self.has_events)
        clear_state_action.triggered.connect(self.clear_state)
        menu.addAction(clear_state_action)

        menu.exec(self.mapToGlobal(pos))

    def store_state(self):
        self.menuActionTriggered.emit(MenuAction.STORE_STATE, dict(slot=self.id))
        self.has_events = True
        self.update_appearance()

    def recall_state(self):
        self.menuActionTriggered.emit(MenuAction.RECALL_STATE, dict(slot=self.id))

    def combine_state(self):
        self.menuActionTriggered.emit(MenuAction.COMBINE_STATE, dict(slot=self.id))

    def clear_state(self):
        self.menuActionTriggered.emit(MenuAction.CLEAR_MEMORY_STATE, dict(slot=self.id))
        self.has_events = False
        self.update_appearance()
