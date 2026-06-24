from PySide6.QtCore import Slot, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QLayout,
    QWidget,
)

from pytopaint.layout import dict_to_yaml
from pytopaint.widgets.biplot import Biplot


class BiplotGrid(QWidget):
    resizeTriggered = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setSpacing(5)
        self.grid_layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

        self.setLayout(self.grid_layout)

    def add_biplot(self, biplot: Biplot, coords: tuple[int, int]) -> None:
        row, col = coords
        biplot.removeTriggered.connect(self.remove_biplot)
        self.resizeTriggered.connect(biplot.resize)
        self.grid_layout.addWidget(biplot, row, col)

    @Slot(object)
    def remove_biplot(self, biplot: Biplot) -> None:
        self.grid_layout.setEnabled(False)

        self.grid_layout.removeWidget(biplot)
        biplot.deleteLater()

        self.grid_layout.setEnabled(True)
        self.grid_layout.update()

    @property
    def rows(self) -> int:
        if self.grid_layout.count() == 0:
            return 0
        return (
            max(
                self.grid_layout.getItemPosition(i)[0]
                for i in range(self.grid_layout.count())
            )
            + 1
        )

    @property
    def columns(self) -> int:
        if self.grid_layout.count() == 0:
            return 0
        return (
            max(
                self.grid_layout.getItemPosition(i)[1]
                for i in range(self.grid_layout.count())
            )
            + 1
        )

    def _to_dict(self) -> dict[tuple[int, int], tuple[str, str]]:
        return {
            self._get_biplot_coords(i): self._get_biplot_labels(i)
            for i in range(self.grid_layout.count())
        }

    def to_yaml(self) -> list[list[list[str, str]]]:
        return dict_to_yaml(self._to_dict())

    def _get_biplot(self, index: int) -> Biplot:
        return self.grid_layout.itemAt(index).widget()

    def _get_biplot_labels(self, index: int) -> tuple[str, str]:
        return self._get_biplot(index).labels

    def _get_biplot_coords(self, index: int) -> tuple[int, int]:
        return self.grid_layout.getItemPosition(index)[:2]

    def position_empty(self, coords: tuple[int, int]):
        return self.grid_layout.itemAtPosition(*coords) is None

    @property
    def empty_coords(self) -> list[tuple[int, int]]:
        return [
            (x, y)
            for x in range(self.rows)
            for y in range(self.columns)
            if self.position_empty((x, y))
        ]

    def get_biplots(self) -> list[Biplot]:
        return [self._get_biplot(i) for i in range(self.grid_layout.count())]
