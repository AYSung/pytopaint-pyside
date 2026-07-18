from typing import Protocol

from PySide6.QtCore import Signal
from PySide6.QtGui import (
    QKeySequence,
    QShortcut,
)

from pytopaint.actions import MenuAction
from pytopaint.colors import COLOR_SHORTCUTS, Color


class PaintWidget(Protocol):
    menuActionTriggered: Signal = Signal(int, dict)
    active_color: Color


def configure_paint_shortcuts(widget: PaintWidget) -> None:

    def _color_shortcut(key: str, color: Color) -> QShortcut:
        shortcut = QShortcut(QKeySequence(key), widget)
        shortcut.activated.connect(
            lambda: widget.menuActionTriggered.emit(
                MenuAction.SET_ACTIVE, dict(color=color)
            )
        )

    for key, color in COLOR_SHORTCUTS:
        _color_shortcut(key, color)

    exact_zap_current_color = QShortcut(QKeySequence('E'), widget)
    exact_zap_current_color.activated.connect(
        lambda: widget.menuActionTriggered.emit(
            MenuAction.EXACT_ZAP, dict(color=widget.active_color)
        )
    )
    zap_current_color = QShortcut(QKeySequence('Shift+E'), widget)
    zap_current_color.activated.connect(
        lambda: widget.menuActionTriggered.emit(
            MenuAction.ZAP, dict(color=widget.active_color)
        )
    )
    zap_all = QShortcut(QKeySequence('Ctrl+E'), widget)
    zap_all.activated.connect(
        lambda: widget.menuActionTriggered.emit(MenuAction.ZAP_ALL, dict())
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
