import sys
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMenu,
    QMainWindow,
    QGridLayout,
    QWidget,
    QSizePolicy,
    QStyleOption,
    QStyle,
)
from PySide6.QtGui import QPixmap, QPainter, QPen, QFont, QMouseEvent, QAction
from PySide6.QtCore import Slot, Qt, QPoint, QRect
import numpy as np

import math

import flowkit

# import polars as pl
import pandas as pd

from pytopaint.io import test_df, bin_df, LINEAR_PARAMETERS

RESOLUTION = 256


class DotPlot(QLabel):
    def __init__(self):
        super().__init__()
        canvas = QPixmap(RESOLUTION, RESOLUTION)
        canvas.fill("#121010")
        self.setPixmap(canvas)

        self.last_x, self.last_y = None, None
        self.selection_geometry = []

    def mouseMoveEvent(self, e: QMouseEvent):
        pos = e.position()
        self.selection_geometry += [[pos.x(), pos.y()]]
        if self.last_x is None:  # First event.
            self.last_x = pos.x()
            self.last_y = pos.y()
            return  # Ignore the first time.

        canvas = self.pixmap()
        painter = QPainter(canvas)
        pen = QPen()
        pen.setColor("#d12f2f")
        painter.setPen(pen)
        painter.drawLine(self.last_x, self.last_y, pos.x(), pos.y())
        painter.end()
        self.setPixmap(canvas)

        self.last_x = pos.x()
        self.last_y = pos.y()

    def mouseReleaseEvent(self, e: QMouseEvent):
        print(self.selection_geometry)
        self.last_x = None
        self.last_y = None
        self.selection_geometry = []

        self.render_plot()

    def set_working_data(self, df: pd.DataFrame, x: str, y: str):
        self.x_label = x
        self.y_label = y
        self.working_df = df[[x, y]].drop_duplicates(subset=[x, y])

    def render_plot(self):
        canvas = self.pixmap()
        canvas.fill("#121010")
        painter = QPainter(canvas)
        pen = QPen()
        pen.setColor("#bababa")
        painter.setPen(pen)
        painter.translate(0, 255)
        painter.scale(1, -1)
        painter.drawPointsNp(
            self.working_df[self.x_label].to_numpy(),
            self.working_df[self.y_label].to_numpy(),
        )
        painter.end()
        self.setPixmap(canvas)
        self.update()


class XAxis(QLabel):
    def __init__(self):
        super().__init__()
        canvas = QPixmap(RESOLUTION, 50)
        canvas.fill("#00000000")
        self.setPixmap(canvas)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def draw_axis(self, x_label: str):
        canvas = self.pixmap()
        canvas.fill("#00000000")
        painter = QPainter(canvas)
        pen = QPen()
        pen.setColor("#bababa")
        painter.setPen(pen)
        painter.drawLine(QPoint(0, 4), QPoint(RESOLUTION - 1, 4))

        label_y = 11
        tick_y0 = 4
        tick_y1 = tick_y0 + 4

        if x_label in LINEAR_PARAMETERS:
            painter.drawLine(QPoint(0, tick_y0), QPoint(0, tick_y1))
            painter.drawText(
                QRect(0, label_y, 40, 20),
                "0",
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            )
            painter.drawLine(QPoint(50, tick_y0), QPoint(50, tick_y1))
            painter.drawLine(QPoint(100, tick_y0), QPoint(100, tick_y1))
            painter.drawText(
                QRect(80, label_y, 40, 20),
                "1e6",
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            )
            painter.drawLine(QPoint(150, tick_y0), QPoint(150, tick_y1))
            painter.drawLine(QPoint(200, tick_y0), QPoint(200, tick_y1))
            painter.drawText(
                QRect(180, label_y, 40, 20),
                "2e6",
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            )
            painter.drawLine(QPoint(250, tick_y0), QPoint(250, tick_y1))
        else:
            painter.drawLine(QPoint(10, tick_y0), QPoint(10, tick_y1))
            painter.drawLine(QPoint(28, tick_y0), QPoint(28, tick_y1))
            painter.drawText(
                QRect(8, label_y, 40, 20),
                "0",
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            )
            painter.drawLine(QPoint(46, tick_y0), QPoint(46, tick_y1))
            painter.drawLine(QPoint(102, tick_y0), QPoint(102, tick_y1))
            painter.drawText(
                QRect(82, 10, 40, 20),
                "1e3",
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            )
            painter.drawLine(QPoint(167, tick_y0), QPoint(167, tick_y1))
            painter.drawText(
                QRect(147, label_y, 40, 20),
                "1e4",
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            )
            painter.drawLine(QPoint(233, tick_y0), QPoint(233, tick_y1))
            painter.drawText(
                QRect(213, label_y, 40, 20),
                "1e5",
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            )

        font = QFont()
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            canvas.rect(),
            x_label,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
        )
        painter.end()
        self.setPixmap(canvas)
        self.update()


class YAxis(QLabel):
    def __init__(self):
        super().__init__()
        canvas = QPixmap(50, RESOLUTION)
        canvas.fill("#00000000")
        self.setPixmap(canvas)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def draw_axis(self, y_label: str) -> None:
        canvas = self.pixmap()
        canvas.fill("#00000000")
        painter = QPainter(canvas)
        pen = QPen()
        pen.setColor("#bababa")
        painter.setPen(pen)
        painter.drawLine(QPoint(45, 0), QPoint(45, RESOLUTION - 1))

        tick_x0 = 41
        tick_x1 = tick_x0 + 4

        if y_label in LINEAR_PARAMETERS:
            painter.drawLine(
                QPoint(tick_x0, RESOLUTION - 1), QPoint(tick_x1, RESOLUTION - 1)
            )
            painter.drawText(
                QRect(-2, 238, 40, 20),
                "0",
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            )
            painter.drawLine(QPoint(tick_x0, 205), QPoint(tick_x1, 205))
            painter.drawLine(QPoint(tick_x0, 155), QPoint(tick_x1, 155))
            painter.drawText(
                QRect(-2, 143, 40, 20),
                "1e6",
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            )
            painter.drawLine(QPoint(tick_x0, 105), QPoint(tick_x1, 105))
            painter.drawLine(QPoint(tick_x0, 55), QPoint(tick_x1, 55))
            painter.drawText(
                QRect(-2, 43, 40, 20),
                "2e6",
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            )
            painter.drawLine(QPoint(tick_x0, 5), QPoint(tick_x1, 5))
        else:
            painter.drawLine(
                QPoint(tick_x0, RESOLUTION - 234), QPoint(tick_x1, RESOLUTION - 234)
            )
            painter.drawText(
                QRect(-2, RESOLUTION - 242, 40, 40),
                "1e5",
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
            )
            painter.drawLine(
                QPoint(tick_x0, RESOLUTION - 168), QPoint(tick_x1, RESOLUTION - 168)
            )
            painter.drawText(
                QRect(-2, RESOLUTION - 176, 40, 40),
                "1e4",
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
            )
            painter.drawLine(
                QPoint(tick_x0, RESOLUTION - 103), QPoint(tick_x1, RESOLUTION - 103)
            )
            painter.drawText(
                QRect(-2, RESOLUTION - 111, 40, 40),
                "1e3",
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
            )
            painter.drawLine(
                QPoint(tick_x0, RESOLUTION - 47), QPoint(tick_x1, RESOLUTION - 47)
            )
            painter.drawLine(
                QPoint(tick_x0, RESOLUTION - 29), QPoint(tick_x1, RESOLUTION - 29)
            )
            painter.drawText(
                QRect(-2, RESOLUTION - 37, 40, 40),
                "0",
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
            )
            painter.drawLine(
                QPoint(tick_x0, RESOLUTION - 11), QPoint(tick_x1, RESOLUTION - 11)
            )
        painter.translate(0, 256)
        painter.rotate(-90)
        font = QFont()
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            QRect(0, 0, 255, 20),
            y_label,
            Qt.AlignmentFlag.AlignLeft,
        )
        painter.end()

        self.setPixmap(canvas)
        self.update()


class Biplot(QWidget):
    def __init__(self, df: pd.DataFrame, x_label: str, y_label: str):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        # self.setStyleSheet("margin: 5px;")

        self.x_label = x_label
        self.y_label = y_label
        self.df = df

        self.channels = [col for col in self.df.columns if col != "Time"]

        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-weight: bold; margin-bottom: 8px")

        self.plot = DotPlot()

        self.x_axis = XAxis()
        self.x_axis.customContextMenuRequested.connect(self.x_context_menu)

        self.y_axis = YAxis()
        self.y_axis.customContextMenuRequested.connect(self.y_context_menu)

        layout = QGridLayout()
        layout.setSpacing(0)
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
        self.update_plot()

    def update_plot(self):
        self.plot.set_working_data(self.df, self.x_label, self.y_label)
        self.plot.render_plot()

        self.x_axis.draw_axis(self.x_label)
        self.y_axis.draw_axis(self.y_label)

        self.title_label.setText(f"{self.x_label} vs {self.y_label}")

    def y_context_menu(self, pos):
        menu = QMenu()
        for channel in self.channels:
            menu.addAction(channel)

        action = menu.exec(self.y_axis.mapToGlobal(pos))
        if action:
            self.y_label = action.text()
            self.update_plot()

    def x_context_menu(self, pos):
        menu = QMenu()
        for channel in self.channels:
            menu.addAction(channel)

        action = menu.exec(self.x_axis.mapToGlobal(pos))
        if action:
            self.x_label = action.text()
            self.update_plot()

    def paintEvent(self, pe):
        o = QStyleOption()
        o.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, o, p, self)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PytoPaint")
        self.resolution = 256
        self.df = bin_df(test_df(), n_bins=self.resolution)

        # self.setStyleSheet("QMainWindow { background-color: #121010; }")

        menu_bar = self.menuBar()
        # menu_bar.setNativeMenuBar(False)
        file_menu = menu_bar.addMenu("&File")
        # 3. Create and add an Action
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        central_widget = QWidget()
        layout = QGridLayout()
        layout.setSpacing(5)
        layout.addWidget(Biplot(self.df, x_label="FSC-A", y_label="SSC-A"), 0, 0)
        layout.addWidget(Biplot(self.df, x_label="SSC-A", y_label="CD45 AF700"), 1, 0)
        layout.addWidget(Biplot(self.df, x_label="FSC-A", y_label="FSC-H"), 2, 0)
        layout.addWidget(Biplot(self.df, x_label="CD5 BV480", y_label="CD19"), 0, 1)
        layout.addWidget(Biplot(self.df, x_label="CD10", y_label="CD20"), 0, 2)
        central_widget.setLayout(layout)

        self.setCentralWidget(central_widget)


app = QApplication(sys.argv)
window = MainWindow()
window.show()

app.exec()
