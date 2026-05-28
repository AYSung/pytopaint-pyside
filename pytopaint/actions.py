from enum import IntEnum, auto


class MenuAction(IntEnum):
    SET_ACTIVE = auto()
    ZAP = auto()
    EXACT_ZAP = auto()
    ZAP_ALL = auto()
    MERGE = auto()
    HIDE = auto()
    ISOLATE = auto()
    UNDO = auto()
    REDO = auto()
    RESET = auto()
    SUBSAMPLE = auto()
    HIGHLIGHT = auto()
    RECALL = auto()
