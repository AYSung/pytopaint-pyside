# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

from enum import IntEnum, auto


class MenuAction(IntEnum):
    SET_ACTIVE = auto()
    ADD_COLOR = auto()
    OVERRIDE_COLOR = auto()
    ZAP = auto()
    EXACT_ZAP = auto()
    ZAP_ALL = auto()
    ZAP_ALL_BUT = auto()
    MERGE_COLOR = auto()
    UNHIDE_ALL = auto()
    HIDE = auto()
    ISOLATE = auto()
    UNDO = auto()
    REDO = auto()
    RESET = auto()
    SUBSAMPLE = auto()
    HIGHLIGHT = auto()
    TOGGLE_ALL_HIGHLIGHTS = auto()
    REPLACE_STATE = auto()
    MERGE_STATE = auto()
    STORE_STATE = auto()
    STORE_STATE_AND_CLEAR = auto()
    FORGET_STATE = auto()
    STORE_COLOR = auto()
    STORE_COLOR_AND_CLEAR = auto()
    RECALL_COLOR = auto()
    IMMUNOPHENOTYPE = auto()
