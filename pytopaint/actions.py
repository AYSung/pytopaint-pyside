from enum import IntEnum, auto


class MenuAction(IntEnum):
    SET_ACTIVE = auto()
    ZAP = auto()
    EXACT_ZAP = auto()
    ZAP_ALL = auto()
    MERGE_COLOR = auto()
    UNHIDE_ALL = auto()
    HIDE = auto()
    ISOLATE = auto()
    UNDO = auto()
    REDO = auto()
    RESET = auto()
    SUBSAMPLE = auto()
    HIGHLIGHT = auto()
    REPLACE_STATE = auto()
    MERGE_STATE = auto()
    STORE_STATE = auto()
    STORE_STATE_AND_CLEAR = auto()
    STORE_COLOR = auto()
    STORE_COLOR_AND_CLEAR = auto()
    RECALL_COLOR = auto()
