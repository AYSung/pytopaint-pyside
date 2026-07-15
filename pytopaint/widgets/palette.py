# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

import pandas as pd
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QAction, QIcon, QMouseEvent, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMenu,
    QStyle,
    QStyleOption,
    QToolButton,
    QWidget,
)

from pytopaint.actions import MenuAction
from pytopaint.colors import (
    Color,
    events_by_color,
    get_color_map,
    is_zappable,
    ratios_by_color,
)


class Palette(QWidget):
    activeColorChanged = Signal(int)
    menuActionTriggered = Signal(int, dict)
    eventsUpdated = Signal(object, int)
    highlightsUpdated = Signal(list)
    colorPaletteChanged = Signal()

    def __init__(self, memory_states: dict[int, pd.DataFrame]):
        super().__init__()

        layout = QHBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(20, 0, 20, 0)

        self.total_events_label = QLabel()
        self.total_events_label.setFixedWidth(150)
        layout.addWidget(self.total_events_label)

        self.color_labels = {c: ColorLabel(c) for c in Color}
        for color_label in self.color_labels.values():
            layout.addWidget(color_label)
            color_label.menuActionTriggered.connect(self.menuActionTriggered)
            self.highlightsUpdated.connect(color_label.update_highlight)
            self.activeColorChanged.connect(color_label.update_active_color)
            self.eventsUpdated.connect(color_label.update_label)
            self.colorPaletteChanged.connect(color_label.update_palette)

        save_state_label = QLabel('Snapshots:')
        save_state_label.setContentsMargins(0, 0, 10, 0)
        layout.addWidget(save_state_label)
        self.memory_slots = {
            i: MemorySlot(i, memory_states[i] is not None) for i in memory_states.keys()
        }
        for memory_slot in self.memory_slots.values():
            layout.addWidget(
                memory_slot,
            )
            memory_slot.menuActionTriggered.connect(self.menuActionTriggered)

        layout.addStretch()

        self.setLayout(layout)

    @Slot(object)
    def update_labels(self, state: pd.DataFrame):
        events = events_by_color(state.loc[state['visible'], 'color'])
        total_events = state['visible'].sum()
        self.total_events_label.setText(f'Total Events: {total_events:,}')

        self.eventsUpdated.emit(events, total_events)

    def paintEvent(self, _: QStyle.PrimitiveElement):
        o = QStyleOption()
        o.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, o, p, self)

    @Slot(int, object)
    def update_color_memory(self, color: Color, color_state: pd.Series):
        self.color_labels[color].remember_state(color_state)


class ColorLabel(QWidget):
    menuActionTriggered = Signal(int, dict)

    def __init__(self, color: Color, parent=None):
        super().__init__(parent)
        self.color = color
        self.highlight = False
        self.event_count = 0
        self.zappable = False
        self.others_zappable = False
        self.memory = None

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)
        self.setFixedWidth(150)

        layout = QHBoxLayout()

        self.box = QLabel()
        self.box.setFixedSize(12, 12)
        self.update_palette()

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
        percent = self.event_count / total_events if total_events > 0 else 0
        if (self.event_count >= 100) or (self.event_count == 0):
            self.label.setText(_format_percent(percent))
        else:
            self.label.setText(f'{_format_percent(percent)} ({self.event_count})')

        self.zappable = is_zappable(self.color, events)
        self.others_zappable = any(
            v for k, v in events.items() if k not in [self.color, Color.GREY]
        )
        self.ratios = ratios_by_color(
            self.color,
            {color: n / total_events for color, n in sorted(events.items())},
        )

    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.MouseButton.RightButton:
            self.customContextMenuRequested.emit(e.pos())

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

    @Slot()
    def update_palette(self):
        self.box.setStyleSheet(f'background-color: {get_color_map()[self.color]}')

    def context_menu(self, pos):
        def _merge_action(color: Color) -> QAction:
            action = QAction(_color_icon(color), color.label_name)
            action.triggered.connect(
                lambda: self.menuActionTriggered.emit(
                    MenuAction.MERGE_COLOR,
                    dict(source_color=self.color, target_color=color),
                )
            )
            return action

        def _ratio_action(color: Color, label_info: tuple[float, float]) -> QAction:
            action = QAction(
                _color_icon(color),
                f'{_format_ratio(label_info[0])} ({_format_percent(label_info[1])})',
            )
            action.triggered.connect(
                lambda: copy_ratio_to_clipboard(self.ratios[color][0])
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

            zap_all_but = QAction(
                'Zap Others', enabled=self.others_zappable and self.zappable
            )
            zap_all_but.triggered.connect(
                lambda: self.menuActionTriggered.emit(
                    MenuAction.ZAP_ALL_BUT, dict(color=self.color)
                )
            )
            menu.addAction(zap_all_but)

            merge_menu = QMenu('Merge with...')
            merge_menu.setEnabled(self.has_events)

            merge_actions = [
                _merge_action(color) for color in Color if color != self.color
            ]

            for merge_action in merge_actions:
                merge_menu.addAction(merge_action)
            menu.addMenu(merge_menu)
        else:
            zap_all = QAction('Zap All')
            zap_all.triggered.connect(
                lambda: self.menuActionTriggered.emit(MenuAction.ZAP_ALL, dict())
            )
            menu.addAction(zap_all)

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

        if self.color == Color.GREY:
            menu.addSeparator()
            unhide = QAction('Show All Events')
            unhide.triggered.connect(
                lambda: self.menuActionTriggered.emit(MenuAction.UNHIDE_ALL, dict())
            )
            menu.addAction(unhide)

        if self.color != Color.GREY:
            menu.addSeparator()
            remember = QAction('Remember', self, enabled=self.has_events)
            remember.triggered.connect(
                lambda: self.menuActionTriggered.emit(
                    MenuAction.STORE_COLOR, dict(color=self.color)
                )
            )
            menu.addAction(remember)

            remember_and_clear = QAction(
                'Remember && Clear', self, enabled=self.has_events
            )
            # shortcut?
            remember_and_clear.triggered.connect(
                lambda: self.menuActionTriggered.emit(
                    MenuAction.STORE_COLOR_AND_CLEAR, dict(color=self.color)
                )
            )
            menu.addAction(remember_and_clear)

            recall = QAction('Recall', self, enabled=self.memory is not None)
            recall.triggered.connect(
                lambda: self.menuActionTriggered.emit(
                    MenuAction.RECALL_COLOR, dict(color_state=self.memory)
                )
            )
            menu.addAction(recall)

            clear_memory = QAction('Forget', self, enabled=self.memory is not None)
            clear_memory.triggered.connect(self.clear_memory)
            menu.addAction(clear_memory)

            menu.addSection('Ratios')

            ratio_labels = [
                _ratio_action(color, label_info)
                for color, label_info in self.ratios.items()
            ]
            menu.addActions(ratio_labels)

            menu.addSeparator()
            immunophenotyper_action = QAction(
                'Immunophenotype', self, enabled=self.has_events
            )
            immunophenotyper_action.triggered.connect(
                lambda: self.menuActionTriggered.emit(
                    MenuAction.IMMUNOPHENOTYPE, dict(color=self.color)
                )
            )
            menu.addAction(immunophenotyper_action)

        menu.exec(self.mapToGlobal(pos))

    def remember_state(self, color_state: pd.Series):
        self.memory = color_state

    def clear_memory(self):
        self.memory = None


def copy_ratio_to_clipboard(ratio: float):
    clipboard = QApplication.clipboard()

    clipboard.setText(_format_ratio(ratio).partition(':')[0].strip())


def _format_percent(percent: float) -> str:
    return f'{percent:.{1 if (percent == 0) or (percent >= 0.00995) else 2}%}'


def _format_ratio(ratio: float) -> str:
    return f'{ratio:.{1 if ratio >= 1 else 2}f} : 1'


def _color_icon(color: Color) -> QIcon:
    pixmap = QPixmap(16, 12)
    pixmap.fill('#00000000')
    painter = QPainter(pixmap)
    painter.fillRect(0, 0, 12, 12, get_color_map()[color])
    painter.end()
    return QIcon(pixmap)


class MemorySlot(QToolButton):
    menuActionTriggered = Signal(int, dict)

    def __init__(self, id: int, has_events: bool, parent=None):
        super().__init__(parent)
        self.mouse_pressed = False

        self.id = id
        self.has_events = has_events
        self.setText(str(id))
        self.update_appearance()
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

    def mousePressEvent(self, e: QMouseEvent):
        self.mouse_pressed = True
        if e.button() == Qt.MouseButton.RightButton:
            self.customContextMenuRequested.emit(e.pos())

    def mouseReleaseEvent(self, e: QMouseEvent):
        if not self.has_events or not self.mouse_pressed:
            self.mouse_pressed = False
            super().mouseReleaseEvent(e)
            return

        modifiers = e.modifiers()
        if e.button() == Qt.MouseButton.LeftButton:
            if modifiers == Qt.KeyboardModifier.NoModifier:
                self.replace_state()
            elif modifiers == Qt.KeyboardModifier.ShiftModifier:
                self.merge_state()
        elif e.button() == Qt.MouseButton.MiddleButton:
            if modifiers == Qt.KeyboardModifier.NoModifier:
                self.clear_state()

        self.mouse_pressed = False
        super().mouseReleaseEvent(e)

    def update_appearance(self) -> None:
        self.setStyleSheet(
            f'background-color: {"#828282" if self.has_events else "#121212"}'
        )

    def context_menu(self, pos):
        menu = QMenu()
        recall_state_action = QAction('Recall', self, enabled=self.has_events)
        recall_state_action.triggered.connect(self.replace_state)
        menu.addAction(recall_state_action)
        combine_state_action = QAction('Recall Non-Grey', self, enabled=self.has_events)
        combine_state_action.triggered.connect(self.merge_state)
        menu.addAction(combine_state_action)

        menu.addSeparator()

        store_state_action = QAction('Remember', self)
        store_state_action.triggered.connect(self.store_state)
        menu.addAction(store_state_action)
        store_state_and_clear_action = QAction('Remember && Clear', self)
        store_state_and_clear_action.triggered.connect(self.store_state_and_clear)
        menu.addAction(store_state_and_clear_action)
        clear_state_action = QAction('Forget', self, enabled=self.has_events)
        clear_state_action.triggered.connect(self.clear_state)
        menu.addAction(clear_state_action)

        menu.exec(self.mapToGlobal(pos))

    def replace_state(self):
        self.menuActionTriggered.emit(MenuAction.REPLACE_STATE, dict(slot=self.id))

    def merge_state(self):
        self.menuActionTriggered.emit(MenuAction.MERGE_STATE, dict(slot=self.id))

    def store_state(self):
        self.has_events = True
        self.menuActionTriggered.emit(MenuAction.STORE_STATE, dict(slot=self.id))
        self.update_appearance()

    def store_state_and_clear(self):
        self.has_events = True
        self.menuActionTriggered.emit(
            MenuAction.STORE_STATE_AND_CLEAR, dict(slot=self.id)
        )
        self.update_appearance()

    def clear_state(self):
        self.has_events = False
        self.update_appearance()
