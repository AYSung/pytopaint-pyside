from enum import IntEnum, auto


class MenuAction(IntEnum):
    SET_ACTIVE = auto()
    ZAP = auto()
    EXACT_ZAP = auto()
    ZAP_ALL = auto()
    MERGE = auto()
    UNHIDE_ALL = auto()
    HIDE = auto()
    ISOLATE = auto()
    UNDO = auto()
    REDO = auto()
    RESET = auto()
    SUBSAMPLE = auto()
    HIGHLIGHT = auto()
    RECALL_STATE = auto()
    STORE_STATE = auto()
    CLEAR_MEMORY_STATE = auto()
