from PySide6.QtWidgets import (
    QLabel,
    QMenu,
    QGridLayout,
    QWidget,
    QSizePolicy,
    QStyleOption,
    QStyle,
    QApplication,
)
from PySide6.QtGui import QPixmap, QPainter, QPen, QFont, QMouseEvent, QAction
from PySide6.QtCore import Slot, Qt, QPoint, QRect, Signal

# import polars as pl
import pandas as pd

from pytopaint.flowdata import LINEAR_PARAMETERS, sort_channels
from pytopaint.colors import Color, COLOR_RGB_MAP, BACKGROUND, indices_by_color
from pytopaint.config import appconfig


class Biplot(QWidget):
    pointsSelected = Signal(object, str, str, QMouseEvent)

    def __init__(
        self,
        df: pd.DataFrame,
        x_label: str,
        y_label: str,
        axis_ticks: dict[str, tuple[int, str]],
    ):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.df = df
        channels = sort_channels([col for col in df.columns if col not in ['color']])
        x_label = x_label if x_label in channels else None
        y_label = y_label if y_label in channels else None

        self.x_axis = XAxis(x_label, channels, axis_ticks)
        self.x_axis.labelChanged.connect(self.update_plot_data)
        self.x_axis.labelChanged.connect(self.update_title)
        self.y_axis = YAxis(y_label, channels, axis_ticks)
        self.y_axis.labelChanged.connect(self.update_plot_data)
        self.y_axis.labelChanged.connect(self.update_title)

        self.plot = DotPlot()
        self.update_plot_data()
        self.plot.pointsSelected.connect(self.points_selected)

        self.title_label = QLabel()
        self.title_label.setStyleSheet('font-weight: bold; margin-bottom: 6px')
        self.title_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.title_label.customContextMenuRequested.connect(self.title_context_menu)
        self.update_title()

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

    @Slot(object)
    def set_data(self, df: pd.DataFrame):
        self.df = df
        self.update_plot_data()

    def update_plot_data(self):
        if self.x_axis.label is None or self.y_axis.label is None:
            return

        df = self.df[[self.x_axis.label, self.y_axis.label, 'color']].drop_duplicates()
        self.plot.update_working_data(
            x_data=df[self.x_axis.label],
            y_data=df[self.y_axis.label],
            color_data=df['color'],
        )

    def copy_plot_to_clipboard(self):
        y_label = self.y_axis.label
        x_label = self.x_axis.label

        canvas = QPixmap(appconfig.resolution + 45, appconfig.resolution + 45)
        canvas.fill('#ffffff')
        painter = QPainter(canvas)
        painter.save()
        painter.translate(45, appconfig.resolution - 1)
        painter.scale(1, -1)

        non_highlight_colors = [
            color
            for color in self.plot.color_indices.keys()
            if color not in self.plot.highlighted_colors
        ]

        for color in non_highlight_colors + self.plot.highlighted_colors:
            self.plot.draw_color(
                color, painter, COLOR_RGB_MAP | {Color.WHITE: '#000000'}
            )

        painter.restore()
        pen = QPen()
        pen.setColor('#000000')
        painter.setPen(pen)
        painter.save()
        painter.translate(45, appconfig.resolution - 1)

        tick_y0 = 0
        tick_y1 = tick_y0 + 4
        label_y = tick_y1 + 3
        X_MAX = appconfig.resolution - 1

        painter.drawLine(QPoint(0, tick_y0), QPoint(X_MAX, tick_y0))

        x_axis_ticks = self.x_axis.axis_ticks[x_label]

        for tick, _ in x_axis_ticks:
            painter.drawLine(QPoint(tick, tick_y0), QPoint(tick, tick_y1))

        axis_labels = (
            [(4, '0')] + x_axis_ticks[1:]
            if x_label in LINEAR_PARAMETERS
            else x_axis_ticks
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
            QRect(0, 0, appconfig.resolution - 1, 45),
            x_label,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
        )

        painter.restore()

        tick_x0 = 41
        tick_x1 = tick_x0 + 4
        label_x = -2
        Y_MAX = appconfig.resolution - 1

        painter.drawLine(QPoint(tick_x1, 0), QPoint(tick_x1, Y_MAX))

        y_axis_ticks = self.y_axis.axis_ticks[y_label]

        for tick, _ in y_axis_ticks:
            painter.drawLine(
                QPoint(tick_x0, Y_MAX - tick),
                QPoint(tick_x1, Y_MAX - tick),
            )

        axis_labels = (
            [(4, '0')] + y_axis_ticks[1:]
            if y_label in LINEAR_PARAMETERS
            else y_axis_ticks
        )

        for tick, label in filter(lambda x: x is not None, axis_labels):
            painter.drawText(
                QRect(label_x, Y_MAX - tick - 12, 40, 20),
                label,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            )

        painter.translate(0, appconfig.resolution - 1)
        painter.rotate(-90)
        font = QFont()
        font.setWeight(QFont.Weight(800))

        painter.setFont(font)
        painter.drawText(
            QRect(0, 1, appconfig.resolution - 1, 20),
            y_label,
            Qt.AlignmentFlag.AlignLeft,
        )

        painter.end()
        clipboard = QApplication.clipboard()
        clipboard.setPixmap(canvas)

    def transpose_axes(self):
        x_label = self.x_axis.label
        y_label = self.y_axis.label
        self.x_axis.label = y_label
        self.y_axis.label = x_label
        self.update_plot_data()
        self.update_title()

    def title_context_menu(self, pos):
        menu = QMenu()
        transpose = QAction(
            'Transpose Axes',
            enabled=self.x_axis.label is not None and self.y_axis.label is not None,
        )
        transpose.triggered.connect(self.transpose_axes)
        menu.addAction(transpose)
        menu.addSeparator()
        copy = QAction(
            'Copy to Clipboard',
            enabled=self.x_axis.label is not None and self.y_axis.label is not None,
        )
        copy.triggered.connect(self.copy_plot_to_clipboard)
        menu.addAction(copy)
        menu.exec(self.mapToGlobal(pos))

    @Slot(str)
    def update_title(self, _: str = None):
        if self.x_axis.label is None or self.y_axis.label is None:
            title = ''
        else:
            title = f'{self.y_axis.label} vs {self.x_axis.label}'

        self.title_label.setText(title)

    @Slot(object, QMouseEvent)
    def points_selected(
        self, selection_geometry: list[tuple[int, int]], e: QMouseEvent
    ):
        self.pointsSelected.emit(
            selection_geometry, self.x_axis.label, self.y_axis.label, e
        )

    def paintEvent(self, pe):
        o = QStyleOption()
        o.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, o, p, self)


class DotPlot(QLabel):
    pointsSelected = Signal(object, QMouseEvent)

    def __init__(self):
        super().__init__()
        canvas = QPixmap(appconfig.resolution, appconfig.resolution)
        canvas.fill(BACKGROUND)
        self.setPixmap(canvas)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self.last_x, self.last_y = None, None
        self.selection_geometry = []
        self.highlighted_colors = []
        self.color_indices = None

    def mouseMoveEvent(self, e: QMouseEvent):
        if self.color_indices is None:
            return

        if e.buttons() == Qt.MouseButton.MiddleButton:
            return

        pos = e.position()
        self.selection_geometry += [(pos.x(), appconfig.resolution - pos.y())]
        if self.last_x is None:  # First event.
            self.last_x = pos.x()
            self.last_y = pos.y()
            return  # Ignore the first time.

        canvas = self.pixmap()
        painter = QPainter(canvas)
        pen = QPen()
        if e.buttons() == Qt.MouseButton.LeftButton:
            pen.setColor(COLOR_RGB_MAP[self.active_color])
        elif e.buttons() == Qt.MouseButton.RightButton:
            pen.setColor(COLOR_RGB_MAP[Color.GREY])
        painter.setPen(pen)
        painter.drawLine(self.last_x, self.last_y, pos.x(), pos.y())
        painter.end()
        self.setPixmap(canvas)

        self.last_x = pos.x()
        self.last_y = pos.y()

    def mouseReleaseEvent(self, e: QMouseEvent):
        if self.color_indices is None:
            return

        self.pointsSelected.emit(
            self.selection_geometry,
            e,
        )

        self.last_x = None
        self.last_y = None
        self.selection_geometry = []

        self.render_plot()

    def update_working_data(
        self, x_data: pd.Series, y_data: pd.Series, color_data: pd.Series
    ):
        self.x_data = x_data
        self.y_data = y_data
        self.color_indices = indices_by_color(color_data)

        self.render_plot()

    @Slot(list)
    def update_highlighted_colors(self, highlighted_colors: list[Color]):
        self.highlighted_colors = highlighted_colors
        self.render_plot()

    @Slot(int)
    def set_active_color(self, color: Color):
        self.active_color = color

    def draw_color(
        self,
        color: Color,
        painter: QPainter,
        color_map: dict[Color, str] = COLOR_RGB_MAP,
    ) -> None:
        pen = QPen()
        pen.setColor(color_map[color])
        pen.setWidth(2 if color in self.highlighted_colors else 1)
        painter.setPen(pen)

        index = self.color_indices.get(color, pd.Index([]))
        painter.drawPointsNp(
            self.x_data.loc[index].to_numpy(dtype='uint16'),
            self.y_data.loc[index].to_numpy(dtype='uint16'),
        )

    def render_plot(
        self,
    ):
        if self.color_indices is None:
            return

        canvas = self.pixmap()
        canvas.fill(BACKGROUND)
        painter = QPainter(canvas)
        painter.translate(0, appconfig.resolution - 1)
        painter.scale(1, -1)

        non_highlight_colors = [
            color
            for color in self.color_indices.keys()
            if color not in self.highlighted_colors
        ]

        for color in non_highlight_colors + self.highlighted_colors:
            self.draw_color(color, painter)

        painter.end()
        self.setPixmap(canvas)
        self.update()


class XAxis(QLabel):
    labelChanged = Signal()

    def __init__(
        self, label: str, channels: list[str], axis_ticks: dict[str, tuple[int, str]]
    ):
        super().__init__()
        self.label = label
        self.channels = channels
        self.axis_ticks = axis_ticks

        canvas = QPixmap(appconfig.resolution, 45)
        canvas.fill('#00000000')
        self.setPixmap(canvas)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

        self.draw_axis()

    def draw_axis(self):
        canvas = self.pixmap()
        canvas.fill('#00000000')
        painter = QPainter(canvas)
        pen = QPen()
        pen.setColor('#bababa')
        painter.setPen(pen)

        label_y = 11
        tick_y0 = 4
        tick_y1 = tick_y0 + 4
        X_MAX = appconfig.resolution - 1

        painter.drawLine(QPoint(0, tick_y0), QPoint(X_MAX, tick_y0))

        if self.label is not None:
            axis_ticks = self.axis_ticks[self.label]

            for tick, _ in axis_ticks:
                painter.drawLine(QPoint(tick, tick_y0), QPoint(tick, tick_y1))

            axis_labels = (
                [(4, '0')] + axis_ticks[1:]
                if self.label in LINEAR_PARAMETERS
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
        self.setPixmap(canvas)
        self.update()

    def context_menu(self, pos):
        menu = QMenu()
        for channel in self.channels:
            menu.addAction(channel)

        action = menu.exec(self.mapToGlobal(pos))
        if action and (action != self.label):
            self.update_axis_label(action.text())

    def update_axis_label(self, label: str):
        self.label = label
        self.draw_axis()
        self.labelChanged.emit()


class YAxis(QLabel):
    labelChanged = Signal()

    def __init__(
        self, label: str, channels: list[str], axis_ticks: dict[str, tuple[int, str]]
    ):
        super().__init__()
        self.label = label
        self.channels = channels
        self.axis_ticks = axis_ticks

        canvas = QPixmap(45, appconfig.resolution)
        canvas.fill('#00000000')

        self.setPixmap(canvas)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

        self.draw_axis()

    def draw_axis(self) -> None:
        canvas = self.pixmap()
        canvas.fill('#00000000')
        painter = QPainter(canvas)
        pen = QPen()
        pen.setColor('#bababa')
        painter.setPen(pen)

        label_x = -7
        tick_x0 = 36
        tick_x1 = tick_x0 + 4
        Y_MAX = appconfig.resolution - 1

        painter.drawLine(QPoint(tick_x1, 0), QPoint(tick_x1, Y_MAX))

        if self.label is not None:
            axis_ticks = self.axis_ticks[self.label]

            for tick, _ in axis_ticks:
                painter.drawLine(
                    QPoint(tick_x0, Y_MAX - tick),
                    QPoint(tick_x1, Y_MAX - tick),
                )

            axis_labels = (
                [(4, '0')] + axis_ticks[1:]
                if self.label in LINEAR_PARAMETERS
                else axis_ticks
            )

            for tick, label in filter(lambda x: x is not None, axis_labels):
                painter.drawText(
                    QRect(label_x, Y_MAX - tick - 12, 40, 20),
                    label,
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
                )

            painter.translate(0, appconfig.resolution - 1)
            painter.rotate(-90)
            font = QFont()
            font.setWeight(QFont.Weight(800))
            painter.setFont(font)
            painter.drawText(
                QRect(1, 0, appconfig.resolution - 1, 20),
                self.label,
                Qt.AlignmentFlag.AlignLeft,
            )
        painter.end()
        self.setPixmap(canvas)
        self.update()

    def context_menu(self, pos):
        menu = QMenu()
        for channel in self.channels:
            menu.addAction(channel)

        action = menu.exec(self.mapToGlobal(pos))
        if action and (action != self.label):
            self.update_axis_label(action.text())

    def update_axis_label(self, label: str):
        self.label = label
        self.draw_axis()
        self.labelChanged.emit()
