from PySide6.QtWidgets import (
    QLabel,
    QMenu,
    QGridLayout,
    QWidget,
    QSizePolicy,
    QStyleOption,
    QStyle,
)
from PySide6.QtGui import (
    QPixmap,
    QPainter,
    QPen,
    QFont,
    QMouseEvent,
)
from PySide6.QtCore import Slot, Qt, QPoint, QRect, Signal

# import polars as pl
import pandas as pd

from pytopaint.io import LINEAR_PARAMETERS, sort_channels
from pytopaint.colors import Color, COLOR_RGB_MAP, BACKGROUND

RESOLUTION = 256


class DotPlot(QLabel):
    pointsSelected = Signal(object, str, str, QMouseEvent)

    def __init__(self, df: pd.DataFrame, x_label: str, y_label: str):
        super().__init__()
        canvas = QPixmap(RESOLUTION, RESOLUTION)
        canvas.fill(BACKGROUND)
        self.setPixmap(canvas)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self.df = df
        self.x_label = x_label
        self.y_label = y_label

        self.last_x, self.last_y = None, None
        self.selection_geometry = []
        self.selections = {}
        self.highlight_color = {c.value: False for c in Color}

        self.update_working_data()

    def mouseMoveEvent(self, e: QMouseEvent):
        if e.buttons() == Qt.MouseButton.MiddleButton:
            return

        pos = e.position()
        self.selection_geometry += [[pos.x(), RESOLUTION - pos.y()]]
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
        self.pointsSelected.emit(
            self.selection_geometry,
            self.x_label,
            self.y_label,
            e,
        )

        self.last_x = None
        self.last_y = None
        self.selection_geometry = []

    def update_working_data(self):
        self.working_df = self.df[[self.x_label, self.y_label]].drop_duplicates()

        if not self.selections:
            self.selections = {Color.GREY: self.working_df.index}

        self.render_plot()

    @Slot(object)
    def update_data(self, df: pd.DataFrame):
        self.df = df
        self.update_working_data()

    @Slot(str)
    def update_x_label(self, new_label: str):
        self.x_label = new_label
        self.update_working_data()

    @Slot(str)
    def update_y_label(self, new_label: str):
        self.y_label = new_label
        self.update_working_data()

    @Slot(int)
    def set_active_color(self, color: Color):
        self.active_color = color

    @Slot(int, bool)
    def update_highlight(self, color: Color, is_highlight: bool):
        self.highlight_color[color] = is_highlight
        if is_highlight:
            self.render_plot(priority_color=color)
        else:
            self.render_plot()

    def draw_color(self, color: Color, index: pd.Index, painter: QPainter) -> None:
        pen = QPen()
        pen.setColor(COLOR_RGB_MAP[color])
        pen.setWidth(2 if self.highlight_color[color] else 1)
        painter.setPen(pen)

        df = self.working_df.loc[self.working_df.index.intersection(index)]
        painter.drawPointsNp(df[self.x_label].to_numpy(), df[self.y_label].to_numpy())

    @Slot(object)
    def render_plot(
        self, selections: dict[Color, pd.Index] = None, priority_color: Color = None
    ):
        canvas = self.pixmap()
        canvas.fill(BACKGROUND)
        painter = QPainter(canvas)
        painter.translate(0, 255)
        painter.scale(1, -1)

        if selections is not None:
            self.selections = selections

        for color, index in self.selections.items():
            self.draw_color(color, index, painter)
        # TODO: draw highlighted colors last

        if priority_color:
            self.draw_color(
                priority_color,
                self.selections.get(priority_color, pd.Index([])),
                painter,
            )

        painter.end()
        self.setPixmap(canvas)
        self.update()


class XAxis(QLabel):
    label_changed = Signal(str)

    def __init__(self, label: str, channels: list[str]):
        super().__init__()
        self.label = label
        self.channels = channels

        canvas = QPixmap(RESOLUTION, 50)
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

        painter.drawLine(QPoint(0, tick_y0), QPoint(RESOLUTION - 1, tick_y0))

        if self.label in LINEAR_PARAMETERS:
            x_ticks = [0, 50, 100, 150, 200, 250]
            for x_tick in x_ticks:
                painter.drawLine(QPoint(x_tick, tick_y0), QPoint(x_tick, tick_y1))

            painter.drawText(
                QRect(0, label_y, 40, 20),
                '0',
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            )
            x_labels = [(100, '1e6'), (200, '2e6')]
            for label_x, label_text in x_labels:
                painter.drawText(
                    QRect(label_x - 20, label_y, 40, 20),
                    label_text,
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                )
        else:
            x_ticks = [10, 28, 46, 102, 167, 233]
            for x_tick in x_ticks:
                painter.drawLine(QPoint(x_tick, tick_y0), QPoint(x_tick, tick_y1))

            x_labels = [(28, '0'), (102, '1e3'), (167, '1e4'), (233, '1e5')]
            for label_x, label_text in x_labels:
                painter.drawText(
                    QRect(label_x - 20, label_y, 40, 20),
                    label_text,
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
            self.label = action.text()
            self.draw_axis()
            self.label_changed.emit(self.label)


class YAxis(QLabel):
    label_changed = Signal(str)

    def __init__(self, label: str, channels: list[str]):
        super().__init__()
        self.label = label
        self.channels = channels

        canvas = QPixmap(50, RESOLUTION)
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

        label_x = -2
        tick_x0 = 41
        tick_x1 = tick_x0 + 4

        painter.drawLine(QPoint(45, 0), QPoint(45, RESOLUTION - 1))
        if self.label in LINEAR_PARAMETERS:
            y_ticks = [255, 205, 155, 105, 55, 5]
            for y_tick in y_ticks:
                painter.drawLine(QPoint(tick_x0, y_tick), QPoint(tick_x1, y_tick))

            y_labels = [(250, '0'), (155, '1e6'), (55, '2e6')]
            for label_y, label_text in y_labels:
                painter.drawText(
                    QRect(label_x, label_y - 12, 40, 20),
                    label_text,
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
                )
        else:
            y_ticks = [22, 88, 153, 209, 227, 245]
            for y_tick in y_ticks:
                painter.drawLine(QPoint(tick_x0, y_tick), QPoint(tick_x1, y_tick))

            y_labels = [(227, '0'), (153, '1e3'), (88, '1e4'), (22, '1e5')]
            for label_y, label_text in y_labels:
                painter.drawText(
                    QRect(label_x, label_y - 12, 40, 20),
                    label_text,
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
                )

        painter.translate(0, RESOLUTION)
        painter.rotate(-90)
        font = QFont()
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            QRect(0, 0, 255, 20),
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
            self.label = action.text()
            self.draw_axis()
            self.label_changed.emit(self.label)


class Biplot(QWidget):
    pointsSelected = Signal(object, str, str, QMouseEvent)

    def __init__(self, df: pd.DataFrame, x_label: str, y_label: str):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        channels = sort_channels([col for col in df.columns if col not in ['color']])

        self.plot = DotPlot(df, x_label, y_label)
        self.plot.pointsSelected.connect(self.pointsSelected)
        self.x_axis = XAxis(x_label, channels)
        self.x_axis.label_changed.connect(self.plot.update_x_label)
        self.x_axis.label_changed.connect(self.update_title)
        self.y_axis = YAxis(y_label, channels)
        self.y_axis.label_changed.connect(self.plot.update_y_label)
        self.y_axis.label_changed.connect(self.update_title)

        self.title_label = QLabel()
        self.title_label.setStyleSheet('font-weight: bold; margin-bottom: 8px')
        self.update_title()

        layout = QGridLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
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
        self.plot.update_data(df)

        channels = [col for col in df.columns if col not in ['color']]
        self.x_axis.channels = channels
        self.y_axis.channels = channels

    @Slot(str)
    def update_title(self, _: str = None):
        self.title_label.setText(f'{self.y_axis.label} vs {self.x_axis.label}')

    def paintEvent(self, pe):
        o = QStyleOption()
        o.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, o, p, self)
