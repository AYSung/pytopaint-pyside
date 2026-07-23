# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

from typing import Protocol

from PySide6.QtCore import Signal
from PySide6.QtGui import (
    QKeySequence,
    QShortcut,
)

from pytopaint.actions import MenuAction
from pytopaint.colors import Color


class PaintWidget(Protocol):
    menuActionTriggered: Signal = Signal(int, dict)
    active_color: Color


def configure_paint_shortcuts(widget: PaintWidget) -> None:

    def _color_shortcut(key: str, color: Color) -> None:
        shortcut = QShortcut(QKeySequence(key), widget)
        shortcut.activated.connect(
            lambda: widget.menuActionTriggered.emit(
                MenuAction.SET_ACTIVE, dict(color=color)
            )
        )

    def _toggle_highlight_shortcut(key: str, color: Color) -> None:
        shortcut = QShortcut(QKeySequence(f'Shift+{key}'), widget)
        shortcut.activated.connect(
            lambda: widget.menuActionTriggered.emit(
                MenuAction.HIGHLIGHT, dict(color=color)
            )
        )

    def _exact_zap_shortcut(key: str, color: Color) -> None:
        shortcut = QShortcut(QKeySequence(f'Ctrl+{key}'), widget)
        shortcut.activated.connect(
            lambda: widget.menuActionTriggered.emit(
                MenuAction.EXACT_ZAP, dict(color=color)
            )
        )

    COLOR_SHORTCUTS = [
        ('F', Color.RED),
        ('D', Color.GREEN),
        ('S', Color.BLUE),
        ('V', Color.MAGENTA),
        ('C', Color.CYAN),
        ('X', Color.YELLOW),
        ('A', Color.WHITE),
    ]
    for key, color in COLOR_SHORTCUTS:
        _color_shortcut(key, color)
        _toggle_highlight_shortcut(key, color)
        _exact_zap_shortcut(key, color)

    exact_zap_current_color = QShortcut(QKeySequence('E'), widget)
    exact_zap_current_color.activated.connect(
        lambda: widget.menuActionTriggered.emit(
            MenuAction.EXACT_ZAP, dict(color=widget.active_color)
        )
    )

    zap_all = QShortcut(QKeySequence('Ctrl+E'), widget)
    zap_all.activated.connect(
        lambda: widget.menuActionTriggered.emit(MenuAction.ZAP_ALL, dict())
    )

    toggle_all_highlights = QShortcut(QKeySequence('Shift+E'), widget)
    toggle_all_highlights.activated.connect(
        lambda: widget.menuActionTriggered.emit(
            MenuAction.TOGGLE_ALL_HIGHLIGHTS, dict()
        )
    )

    undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, widget)
    undo_shortcut.activated.connect(
        lambda: widget.menuActionTriggered.emit(MenuAction.UNDO, dict())
    )
    redo_shortcut = QShortcut(QKeySequence('Ctrl+Shift+Z'), widget)
    redo_shortcut.activated.connect(
        lambda: widget.menuActionTriggered.emit(MenuAction.REDO, dict())
    )

    reset_shortcut = QShortcut(QKeySequence('Ctrl+Shift+R'), widget)
    reset_shortcut.activated.connect(
        lambda: widget.menuActionTriggered.emit(MenuAction.RESET, dict())
    )
    unhide_all_shortcut = QShortcut(QKeySequence('Ctrl+R'), widget)
    unhide_all_shortcut.activated.connect(
        lambda: widget.menuActionTriggered.emit(MenuAction.UNHIDE_ALL, dict())
    )

    hide_events_shortcut = QShortcut(QKeySequence('Backspace'), widget)
    hide_events_shortcut.activated.connect(
        lambda: widget.menuActionTriggered.emit(
            MenuAction.HIDE, dict(color=widget.active_color)
        )
    )

    isolate_events_shortcut = QShortcut(QKeySequence('Return'), widget)
    isolate_events_shortcut.activated.connect(
        lambda: widget.menuActionTriggered.emit(
            MenuAction.ISOLATE, dict(color=widget.active_color)
        )
    )

    hide_grey_shortcut = QShortcut(QKeySequence('Shift + Return'), widget)
    hide_grey_shortcut.activated.connect(
        lambda: widget.menuActionTriggered.emit(MenuAction.HIDE, dict(color=Color.GREY))
    )
