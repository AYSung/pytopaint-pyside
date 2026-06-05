from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QGridLayout,
    QLayout,
)

from pytopaint.layout import dict_to_yaml
from pytopaint.widgets.biplot import Biplot


class BiplotGrid(QGridLayout):
    def __init__(self) -> None:
        super().__init__()
        self.setSpacing(5)
        self.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)

    def add_biplot(self, biplot: Biplot, coords: tuple[int, int]) -> None:
        row, col = coords
        self.addWidget(biplot, row, col)

    @Slot(object)
    def remove_biplot(self, biplot: Biplot) -> None:
        self.setEnabled(False)

        self.removeWidget(biplot)
        biplot.deleteLater()

        self.setEnabled(True)
        self.update()

    @property
    def rows(self) -> int:
        return max(self.getItemPosition(i)[0] for i in range(self.count()))

    @property
    def columns(self) -> int:
        return max(self.getItemPosition(i)[1] for i in range(self.count()))

    def _to_dict(self) -> dict[tuple[int, int], tuple[str, str]]:
        return {
            self._get_biplot_coords(i): self._get_biplot_labels(i)
            for i in range(self.count())
        }

    def to_yaml(self) -> list[list[list[str, str]]]:
        return dict_to_yaml(self._to_dict())

    def _get_biplot_labels(self, index: int) -> tuple[str, str]:
        biplot: Biplot = self.itemAt(index)
        return biplot.labels

    def _get_biplot_coords(self, index: int) -> tuple[int, int]:
        return self.getItemPosition(index)[:2]
