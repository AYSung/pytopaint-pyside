# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

import pandas as pd
from PySide6.QtCore import (
    QBuffer,
    QDir,
    QIODevice,
    QMimeData,
    QPoint,
    QRect,
    QRunnable,
    Qt,
    QThreadPool,
    Signal,
    Slot,
)
from PySide6.QtGui import QAction, QFont, QImage, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QLabel,
    QMenu,
    QStyle,
    QStyleOption,
    QWidget,
)

from pytopaint.actions import MenuAction
from pytopaint.colors import (
    BACKGROUND,
    ZAPPABLE_COLORS,
    Color,
    get_color_map,
    indices_by_color,
    sort_colors,
)
from pytopaint.flowdata import PHYSICAL_PARAMETERS, sort_channels
from pytopaint.selection import get_selection_index

AXIS_WIDTH = 40


class Biplot(QWidget):
    removeTriggered = Signal(object)
    updateFinished = Signal()
    menuActionTriggered = Signal(int, dict)
    activeColorChanged = Signal(int)

    def __init__(
        self,
        data: pd.DataFrame,
        axis_ticks: dict[str, list[tuple[int, str]]],
        state: pd.DataFrame,
        x_label: str,
        y_label: str,
        active_color: Color,
        resolution: int,
        highlighted_colors: list[Color],
    ):
        super().__init__()
        self.df = data
        self.state = state
        self.active_color = active_color

        channels = sort_channels(data.columns)
        x_label = x_label if x_label in channels else None
        y_label = y_label if y_label in channels else None

        self.activeColorChanged.connect(self.set_active_color)

        self.plot = DotPlot(
            active_color=active_color,
            resolution=resolution,
            highlighted_colors=highlighted_colors,
        )
        self.plot.pointsSelected.connect(self.handle_selection)
        self.activeColorChanged.connect(self.plot.set_active_color)

        self.x_axis = XAxis(x_label, channels, axis_ticks, resolution=resolution)
        self.x_axis.labelChanged.connect(self.update_plot_data)
        self.x_axis.labelChanged.connect(self.plot.update_plot)
        self.y_axis = YAxis(y_label, channels, axis_ticks, resolution=resolution)
        self.y_axis.labelChanged.connect(self.update_plot_data)
        self.y_axis.labelChanged.connect(self.plot.update_plot)

        self.set_data(self.df, axis_ticks)
        self.update_plot_data(self.state)
        self.plot.update_plot()

        self.title_label = PlotTitle(
            x_label=self.x_axis.label, y_label=self.y_axis.label, resolution=resolution
        )
        self.x_axis.labelChanged.connect(
            lambda: self.title_label.update_title(self.x_axis.label, self.y_axis.label)
        )
        self.y_axis.labelChanged.connect(
            lambda: self.title_label.update_title(self.x_axis.label, self.y_axis.label)
        )
        self.title_label.transposeAxesClicked.connect(self.transpose_axes)
        self.title_label.copyPlotClicked.connect(self.copy_plot_to_clipboard)
        self.title_label.exportPlotClicked.connect(self.export_plot)
        self.title_label.removePlotClicked.connect(self.remove)

        layout = QGridLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.addWidget(
            self.title_label,
            0,
            1,
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom,
        )
        layout.addWidget(self.y_axis, 1, 0, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.plot, 1, 1)
        layout.addWidget(self.x_axis, 2, 1, Qt.AlignmentFlag.AlignTop)

        self.setLayout(layout)

    @Slot(int)
    def set_active_color(self, color: Color) -> None:
        self.active_color = color

    @Slot(object, QMouseEvent)
    def handle_selection(
        self, selection_geometry: list[list[float]], e: QMouseEvent
    ) -> None:
        modifiers = e.modifiers()

        if e.button() == Qt.MouseButton.MiddleButton:
            if modifiers == Qt.KeyboardModifier.NoModifier:
                self.menuActionTriggered.emit(
                    MenuAction.EXACT_ZAP, dict(color=self.active_color)
                )
            elif modifiers == Qt.KeyboardModifier.ShiftModifier:
                self.menuActionTriggered.emit(
                    MenuAction.ZAP, dict(color=self.active_color)
                )
            elif modifiers == Qt.KeyboardModifier.ControlModifier:
                self.menuActionTriggered.emit(MenuAction.ZAP_ALL, dict())
            return

        color = self.active_color
        if e.button() == Qt.MouseButton.LeftButton:
            selection = get_selection_index(
                selection_geometry,
                df=self.df.loc[
                    self.state['visible'] & (self.state['color'] != self.active_color)
                ],
                x_label=self.x_axis.label,
                y_label=self.y_axis.label,
            )
            if modifiers == Qt.KeyboardModifier.NoModifier:
                # add to selection
                action = MenuAction.ADD_COLOR
            elif modifiers == Qt.KeyboardModifier.ShiftModifier:
                # ignore grey events
                action = MenuAction.ADD_COLOR
                selection = selection.intersection(
                    self.state['color'].loc[lambda s: s != Color.GREY].index
                )
            elif modifiers == Qt.KeyboardModifier.ControlModifier:
                # ignore painted
                action = MenuAction.ADD_COLOR
                selection = selection.intersection(
                    self.state['color'].loc[lambda s: s == Color.GREY].index
                )
            elif (
                modifiers
                == Qt.KeyboardModifier.ControlModifier
                | Qt.KeyboardModifier.ShiftModifier
            ):
                # override colors
                action = MenuAction.OVERRIDE_COLOR
            else:
                selection = pd.Index([])

        elif e.button() == Qt.MouseButton.RightButton:
            selection = get_selection_index(
                selection_geometry,
                df=self.df.loc[
                    self.state['visible'] & (self.state.color != Color.GREY)
                ],
                x_label=self.x_axis.label,
                y_label=self.y_axis.label,
            )

            if modifiers == Qt.KeyboardModifier.NoModifier:
                # exact zap color
                action = MenuAction.EXACT_ZAP
                selection = selection.intersection(
                    self.state['color'].loc[lambda s: s == self.active_color].index
                )
            elif modifiers == Qt.KeyboardModifier.ShiftModifier:
                # zap color
                action = MenuAction.ZAP
                selection = selection.intersection(
                    self
                    .state['color']
                    .loc[self.state['color'].isin(ZAPPABLE_COLORS[self.active_color])]
                    .index
                )
            elif modifiers == Qt.KeyboardModifier.ControlModifier:
                # paint grey
                action = MenuAction.OVERRIDE_COLOR
                color = Color.GREY
            else:
                selection = pd.Index([])
        else:
            return

        if not selection.empty:
            self.menuActionTriggered.emit(
                action, dict(color=color, selection=selection)
            )
        else:
            self.plot.update_plot()

    @Slot(object, object, object)
    def update_data(
        self,
        df: pd.DataFrame = None,
        axis_ticks: dict[str, list[tuple[int, str]]] = None,
        state: pd.DataFrame = None,
    ):
        updater = BiplotUpdater(self, df, axis_ticks, state)
        QThreadPool.globalInstance().start(updater)

    def set_data(self, df: pd.DataFrame, axis_ticks: dict[str, list[tuple[int, str]]]):
        self.df = df

        channels = sort_channels(self.df.columns)
        if (self.x_axis.channels != channels) or (self.y_axis.channels != channels):
            self.x_axis.channels = channels
            self.y_axis.channels = channels

        self.x_axis.set_axis_ticks(axis_ticks)
        self.y_axis.set_axis_ticks(axis_ticks)

    @Slot()
    def update_plot_data(self, state: pd.DataFrame = None):
        if state is not None:
            self.state = state

        if self.x_axis.label is None or self.y_axis.label is None:
            self.plot.clear()
            self.plot.update_plot()
            return

        df = (
            self
            .df[[self.x_axis.label, self.y_axis.label]]
            .loc[self.state['visible']]
            .join(self.state['color'])
            .drop_duplicates()
        )

        self.plot.set_working_data(
            x_data=df[self.x_axis.label],
            y_data=df[self.y_axis.label],
            color_data=df['color'],
        )

    def _draw_plot(self, mode: str):
        match mode:
            case 'dark':
                background_color = BACKGROUND
                color_map = get_color_map()
                label_color = '#bababa'
            case 'light':
                background_color = '#ffffff'
                color_map = get_color_map() | {
                    Color.WHITE: '#000000',
                    Color.GREY: '#828282',
                }
                label_color = '#000000'

        resolution = self.plot.resolution
        image = QImage(
            resolution + AXIS_WIDTH,
            resolution + AXIS_WIDTH,
            QImage.Format.Format_ARGB32,
        )
        image.fill('#00000000')
        painter = QPainter(image)
        painter.drawPixmap(
            AXIS_WIDTH,
            0,
            self.plot.draw_plot(background_color=background_color, color_map=color_map),
        )
        painter.drawPixmap(0, 0, self.y_axis.draw_axis(label_color=label_color))
        painter.drawPixmap(
            AXIS_WIDTH, resolution, self.x_axis.draw_axis(label_color=label_color)
        )

        painter.end()
        return image

    def copy_plot_to_clipboard(self, mode: str):
        image = self._draw_plot(mode)

        byte_array = QBuffer()
        byte_array.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(byte_array, 'PNG', quality=100)
        byte_array.close()

        mime_data = QMimeData()
        mime_data.setData('image/png', byte_array.data())
        mime_data.setImageData(image)

        clipboard = QApplication.clipboard()
        clipboard.setMimeData(mime_data)

    def export_plot(self, mode: str):
        image = self._draw_plot(mode)

        file_path, _ = QFileDialog.getSaveFileName(
            parent=None,
            caption='Export PNG',
            dir=QDir.homePath(),
            filter='PNG (*.png)',
        )
        if not file_path:
            return

        image.save(file_path)

    def transpose_axes(self):
        self.set_axes(x_label=self.y_axis.label, y_label=self.x_axis.label)

    def set_axes(self, x_label: str, y_label: str) -> None:
        self.x_axis.label = x_label
        self.y_axis.label = y_label
        self.x_axis.update_axis()
        self.y_axis.update_axis()
        self.update_plot_data()
        self.plot.update_plot()
        self.title_label.update_title(x_label=x_label, y_label=y_label)

    def paintEvent(self, pe):
        o = QStyleOption()
        o.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, o, p, self)

    @property
    def labels(self) -> tuple[str, str]:
        return self.x_axis.label, self.y_axis.label

    @Slot(int)
    def resize(self, resolution: int) -> None:
        self.plot.resize(pixels=resolution)
        self.x_axis.resize(pixels=resolution)
        self.y_axis.resize(pixels=resolution)
        self.title_label.setFixedWidth(resolution)

    @Slot()
    def remove(self) -> None:
        self.removeTriggered.emit(self)


class PlotTitle(QLabel):
    transposeAxesClicked = Signal()
    copyPlotClicked = Signal(str)
    exportPlotClicked = Signal(str)
    removePlotClicked = Signal()

    def __init__(self, x_label: str, y_label: str, resolution: int):
        super().__init__()
        self.x_label, self.y_label = x_label, y_label

        self.setStyleSheet('font-weight: bold; margin-bottom: 6px')
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedWidth(resolution)
        self.update_title(x_label=x_label, y_label=y_label)

    def resize(self, resolution: int) -> None:
        self.setFixedWidth(resolution)

    @Slot(str, str)
    def update_title(self, x_label: str = None, y_label: str = None) -> None:
        self.x_label, self.y_label = x_label, y_label

        if x_label is None or y_label is None:
            title = ''
        else:
            title = f'{y_label} vs {x_label}'

        self.setText(title)

    def context_menu(self, pos) -> None:
        menu = QMenu()
        transpose = QAction(
            'Transpose Axes',
            enabled=self.x_label is not None and self.y_label is not None,
        )
        transpose.triggered.connect(self.transposeAxesClicked)
        menu.addAction(transpose)
        menu.addSeparator()
        copy_light = QAction(
            'Copy to Clipboard (Light)',
            enabled=self.x_label is not None and self.y_label is not None,
        )
        copy_light.triggered.connect(lambda: self.copyPlotClicked.emit('light'))
        menu.addAction(copy_light)
        copy_dark = QAction(
            'Copy to Clipboard (Dark)',
            enabled=self.x_label is not None and self.y_label is not None,
        )
        copy_dark.triggered.connect(lambda: self.copyPlotClicked.emit('dark'))
        menu.addAction(copy_dark)

        menu.addSeparator()

        export_light = QAction(
            'Export as PNG (Light)',
            enabled=self.x_label is not None and self.y_label is not None,
        )
        export_light.triggered.connect(lambda: self.exportPlotClicked.emit('light'))
        menu.addAction(export_light)
        export_dark = QAction(
            'Export as PNG (Dark)',
            enabled=self.x_label is not None and self.y_label is not None,
        )
        export_dark.triggered.connect(lambda: self.exportPlotClicked.emit('dark'))
        menu.addAction(export_dark)

        menu.addSeparator()

        remove_biplot = QAction('Remove Biplot', self)
        remove_biplot.triggered.connect(self.removePlotClicked)
        menu.addAction(remove_biplot)
        menu.exec(self.mapToGlobal(pos))

    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.MouseButton.RightButton:
            self.customContextMenuRequested.emit(e.pos())

        super().mousePressEvent(e)


class DotPlot(QLabel):
    pointsSelected = Signal(object, QMouseEvent)

    def __init__(
        self, active_color: Color, resolution: int, highlighted_colors: list[Color]
    ):
        super().__init__()
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.active_color = active_color
        self.resolution = resolution
        self.highlighted_colors = highlighted_colors

        self.reset_lasso()
        self.set_working_data(x_data=None, y_data=None, color_data=None)
        self.update_plot()

    def mouseMoveEvent(self, e: QMouseEvent):
        if self.color_indices is None:
            return

        if e.buttons() == Qt.MouseButton.MiddleButton:
            return

        pos = e.position()
        self.selection_geometry.append((pos.x(), self.resolution - pos.y()))
        if self.last_x is None:  # First event.
            self.last_x = pos.x()
            self.last_y = pos.y()
            return  # Ignore the first time.

        canvas = self.pixmap()
        painter = QPainter(canvas)
        pen = QPen()
        if e.buttons() == Qt.MouseButton.LeftButton:
            pen.setColor(get_color_map()[self.active_color])
        elif e.buttons() == Qt.MouseButton.RightButton:
            pen.setColor(get_color_map()[Color.GREY])
        painter.setPen(pen)
        painter.drawLine(self.last_x, self.last_y, pos.x(), pos.y())
        painter.end()
        self.setPixmap(canvas)

        self.last_x = pos.x()
        self.last_y = pos.y()

    def mouseReleaseEvent(self, e: QMouseEvent):
        if self.color_indices is None:
            return
        self.pointsSelected.emit(self.selection_geometry, e)
        self.reset_lasso()

    def reset_lasso(self) -> None:
        self.last_x = None
        self.last_y = None
        self.selection_geometry = []

    def set_working_data(
        self, x_data: pd.Series, y_data: pd.Series, color_data: pd.Series
    ):
        self.x_data = x_data
        self.y_data = y_data
        self.color_indices = (
            indices_by_color(color_data) if color_data is not None else None
        )

    @Slot(list)
    def update_highlighted_colors(self, highlighted_colors: list[Color]):
        self.highlighted_colors = highlighted_colors
        self.update_plot()

    @property
    def non_highlighted_colors(self) -> list[Color]:
        return [
            color
            for color in sort_colors(self.color_indices.keys())
            if color not in self.highlighted_colors
        ]

    @Slot(int)
    def set_active_color(self, color: Color):
        self.active_color = color

    def draw_plot(self, background_color: str, color_map: dict[Color, str]) -> QPixmap:
        canvas = QPixmap(self.resolution, self.resolution)
        canvas.fill(background_color)

        if self.color_indices is None:
            return canvas

        painter = QPainter(canvas)
        painter.translate(0, self.resolution - 1)
        painter.scale(1, -1)

        for color in self.non_highlighted_colors + self.highlighted_colors:
            self.draw_color(color, painter, color_map=color_map)

        painter.end()

        return canvas

    def draw_color(
        self,
        color: Color,
        painter: QPainter,
        color_map: dict[Color, str],
    ) -> None:
        pen = QPen()
        pen.setColor(color_map[color])
        pen.setWidth(2 if color in self.highlighted_colors else 1)
        painter.setPen(pen)

        index = self.color_indices.get(color, pd.Index([]))
        painter.drawPointsNp(
            self.x_data.loc[index].to_numpy(),
            self.y_data.loc[index].to_numpy(),
        )

    @Slot()
    def update_plot(self) -> None:
        self.draw_canvas()
        self.set_canvas()

    def draw_canvas(self) -> None:
        self.canvas = self.draw_plot(
            background_color=BACKGROUND, color_map=get_color_map()
        )

    @Slot()
    def set_canvas(self) -> None:
        self.setPixmap(self.canvas)

    def resize(self, pixels: int):
        self.resolution = pixels

    def clear(self) -> None:
        self.set_working_data(x_data=None, y_data=None, color_data=None)


class XAxis(QLabel):
    labelChanged = Signal()

    def __init__(
        self,
        label: str,
        channels: list[str],
        axis_ticks: dict[str, list[tuple[int, str]]],
        resolution: int,
    ):
        super().__init__()
        self.label = label
        self.channels = channels
        self.axis_ticks = axis_ticks
        self.resolution = resolution
        self.setContentsMargins(0, 4, 0, 0)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

        self.update_axis()

    def set_axis_ticks(self, axis_ticks: dict[str, tuple[int, str]]):
        if self.axis_ticks != axis_ticks:
            self.axis_ticks = axis_ticks
            self.update_axis()

        if self.label not in self.axis_ticks.keys():
            self.label = None
            self.labelChanged.emit()

    def resize(self, pixels: int) -> None:
        self.resolution = pixels
        if self.label not in self.axis_ticks.keys():
            self.label = None
            self.labelChanged.emit()
        self.update_axis()

    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.MouseButton.RightButton:
            self.customContextMenuRequested.emit(e.pos())

        super().mousePressEvent(e)

    def draw_axis(
        self,
        label_color: str,
    ) -> QPixmap:
        canvas = QPixmap(self.resolution, AXIS_WIDTH)
        canvas.fill('#00000000')
        painter = QPainter(canvas)
        pen = QPen()
        pen.setColor(label_color)
        painter.setPen(pen)

        label_y = 7
        tick_y0 = 0
        tick_y1 = tick_y0 + 4
        X_MAX = self.resolution - 1

        painter.drawLine(QPoint(0, tick_y0), QPoint(X_MAX, tick_y0))

        if self.label is not None:
            axis_ticks = self.axis_ticks.get(self.label)

            for tick, _ in axis_ticks:
                painter.drawLine(QPoint(tick, tick_y0), QPoint(tick, tick_y1))

            axis_labels = (
                [(4, '0')] + axis_ticks[1:]
                if self.label in PHYSICAL_PARAMETERS
                else axis_ticks
            )

            for tick, label in filter(lambda x: x is not None, axis_labels):
                painter.drawText(
                    QRect(tick - 20, label_y, 40, 20),
                    label,
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                )

            font = QFont()
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(
                canvas.rect(),
                self.label,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
            )
        painter.end()

        return canvas

    def update_axis(self) -> None:
        canvas = self.draw_axis(label_color='#bababa')
        self.setPixmap(canvas)

    def context_menu(self, pos):
        menu = QMenu()
        for channel in self.channels:
            menu.addAction(channel)

        action = menu.exec(self.mapToGlobal(pos))
        if action and (action != self.label):
            self.label = action.text()
            self.update_axis()
            self.labelChanged.emit()


class YAxis(QLabel):
    labelChanged = Signal()

    def __init__(
        self,
        label: str,
        channels: list[str],
        axis_ticks: dict[str, tuple[int, str]],
        resolution: int,
    ):
        super().__init__()
        self.label = label
        self.channels = channels
        self.axis_ticks = axis_ticks
        self.resolution = resolution
        self.setContentsMargins(0, 0, 4, 0)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

        self.update_axis()

    def set_axis_ticks(self, axis_ticks: dict[str, tuple[int, str]]):
        if self.axis_ticks != axis_ticks:
            self.axis_ticks = axis_ticks
            self.update_axis()

        if self.label not in self.axis_ticks.keys():
            self.label = None
            self.labelChanged.emit()

    def resize(self, pixels: int) -> None:
        self.resolution = pixels
        if self.label not in self.axis_ticks.keys():
            self.label = None
            self.labelChanged.emit()
        self.update_axis()

    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.MouseButton.RightButton:
            self.customContextMenuRequested.emit(e.pos())

        super().mousePressEvent(e)

    def draw_axis(
        self,
        label_color: str,
    ) -> QPixmap:
        canvas = QPixmap(AXIS_WIDTH, self.resolution)
        canvas.fill('#00000000')
        painter = QPainter(canvas)
        pen = QPen()
        pen.setColor(label_color)
        painter.setPen(pen)

        label_x = AXIS_WIDTH - 48
        tick_x1 = AXIS_WIDTH - 1
        tick_x0 = tick_x1 - 4
        Y_MAX = self.resolution - 1

        painter.drawLine(QPoint(tick_x1, 0), QPoint(tick_x1, Y_MAX))

        if self.label is not None:
            axis_ticks = self.axis_ticks.get(self.label)

            for tick, _ in axis_ticks:
                painter.drawLine(
                    QPoint(tick_x0, Y_MAX - tick),
                    QPoint(tick_x1, Y_MAX - tick),
                )

            axis_labels = (
                [(4, '0')] + axis_ticks[1:]
                if self.label in PHYSICAL_PARAMETERS
                else axis_ticks
            )

            for tick, label in filter(lambda x: x is not None, axis_labels):
                painter.drawText(
                    QRect(label_x, Y_MAX - tick - 12, 40, 20),
                    label,
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
                )

            painter.translate(0, Y_MAX)
            painter.rotate(-90)
            font = QFont()
            font.setWeight(QFont.Weight(800))
            painter.setFont(font)
            painter.drawText(
                canvas.rect().transposed(),
                self.label,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            )
        painter.end()

        return canvas

    def update_axis(self) -> None:
        canvas = self.draw_axis(label_color='#bababa')
        self.setPixmap(canvas)

    def context_menu(self, pos):
        menu = QMenu()
        for channel in self.channels:
            menu.addAction(channel)

        action = menu.exec(self.mapToGlobal(pos))
        if action and (action != self.label):
            self.label = action.text()
            self.update_axis()
            self.labelChanged.emit()


class BiplotUpdater(QRunnable):
    def __init__(
        self,
        biplot: Biplot,
        data: pd.DataFrame,
        axis_ticks: dict[str, list[tuple[int, str]]],
        state: pd.DataFrame,
    ):
        super().__init__()
        self.biplot = biplot
        self.data = data
        self.axis_ticks = axis_ticks
        self.state = state

    def run(self):
        if self.data is None and self.state is None:
            return
        if self.data is not None:
            self.biplot.set_data(self.data, self.axis_ticks)
        self.biplot.update_plot_data(self.state)
        self.biplot.plot.draw_canvas()
        self.biplot.updateFinished.emit()
