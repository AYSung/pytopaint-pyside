import sys
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMenu,
    QPushButton,
    QDialog,
    QLineEdit,
    QVBoxLayout,
    QMainWindow,
    QGridLayout,
    QWidget,
)
from PySide6.QtGui import QPixmap, QPainter, QPen
from PySide6.QtCore import Slot, Qt, QPoint, QRect
import numpy as np

import math

import flowkit

# import polars as pl
import pandas as pd

from pytopaint.io import test_df, bin_df, LINEAR_PARAMETERS

RESOLUTION = 256


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PytoPaint")

        self.plot = QLabel()
        plot_canvas = QPixmap(RESOLUTION, RESOLUTION)
        plot_canvas.fill("#121010")
        self.plot.setPixmap(plot_canvas)

        self.resolution = 256
        self.x = "FSC-A"
        self.y = "SSC-A"

        self.x_axis = QLabel()
        x_axis_canvas = QPixmap(RESOLUTION, 50)
        x_axis_canvas.fill("#121010")
        self.x_axis.setPixmap(x_axis_canvas)

        self.y_axis = QLabel()
        y_axis_canvas = QPixmap(60, RESOLUTION)
        y_axis_canvas.fill("#121010")
        self.y_axis.setPixmap(y_axis_canvas)

        axis_filler = QLabel()
        axis_filler.setStyleSheet("background-color: #121010;")
        axis_filler.setFixedSize(60, 50)

        self.x_label = QLabel()
        self.x_axis.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.x_axis.customContextMenuRequested.connect(self.x_context_menu)
        self.y_label = QLabel()
        self.y_axis.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.y_axis.customContextMenuRequested.connect(self.y_context_menu)

        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-weight: bold;")

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
        layout.addWidget(
            axis_filler, 2, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop
        )

        central_widget = QWidget()
        central_widget.setLayout(layout)

        self.setCentralWidget(central_widget)

        self.dot_plot()

    @Slot()
    def dot_plot(self):
        df = bin_df(test_df(), n_bins=self.resolution).drop_duplicates(
            subset=[self.x, self.y]
        )

        canvas = self.plot.pixmap()
        canvas.fill("#121010")
        painter = QPainter(canvas)
        pen = QPen()
        pen.setColor("#bababa")
        painter.setPen(pen)
        painter.drawPointsNp(df[self.x].to_numpy(), RESOLUTION - df[self.y].to_numpy())
        painter.end()
        self.plot.setPixmap(canvas)
        self.plot.update()

        self.draw_x_axis()
        self.draw_y_axis()

        self.x_label.setText(self.x)
        self.y_label.setText(self.y)
        self.title_label.setText(f"{self.x} vs {self.y}")

    def draw_x_axis(self):
        canvas = self.x_axis.pixmap()
        canvas.fill("#121010")
        painter = QPainter(canvas)
        pen = QPen()
        pen.setColor("#bababa")
        painter.setPen(pen)
        painter.drawLine(QPoint(0, 4), QPoint(RESOLUTION - 1, 4))

        label_y = 11

        if self.x in LINEAR_PARAMETERS:
            painter.drawLine(QPoint(0, 4), QPoint(0, 8))
            painter.drawText(
                QRect(0, label_y, 40, 20),
                "0",
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            )
            painter.drawLine(QPoint(50, 4), QPoint(50, 8))
            # painter.drawText(
            #     QRect(30, label_y, 40, 20),
            #     "0.5e6",
            #     Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            # )
            painter.drawLine(QPoint(100, 4), QPoint(100, 8))
            painter.drawText(
                QRect(80, label_y, 40, 20),
                "1e6",
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            )
            painter.drawLine(QPoint(150, 4), QPoint(150, 8))
            # painter.drawText(
            #     QRect(130, label_y, 40, 20),
            #     "1.5e6",
            #     Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            # )
            painter.drawLine(QPoint(200, 4), QPoint(200, 8))
            painter.drawText(
                QRect(180, label_y, 40, 20),
                "2e6",
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            )
            painter.drawLine(QPoint(250, 4), QPoint(250, 8))
            # painter.drawText(
            #     QRect(230, label_y, 40, 20),
            #     "2.5e6",
            #     Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            # )
        else:
            painter.drawLine(QPoint(10, 4), QPoint(10, 8))
            painter.drawLine(QPoint(28, 4), QPoint(28, 8))
            painter.drawText(
                QRect(8, label_y, 40, 20),
                "0",
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            )
            painter.drawLine(QPoint(46, 4), QPoint(46, 8))
            painter.drawLine(QPoint(102, 4), QPoint(102, 8))
            painter.drawText(
                QRect(82, 10, 40, 20),
                "1e3",
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            )
            painter.drawLine(QPoint(167, 4), QPoint(167, 8))
            painter.drawText(
                QRect(147, label_y, 40, 20),
                "1e4",
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            )
            painter.drawLine(QPoint(233, 4), QPoint(233, 8))
            painter.drawText(
                QRect(213, label_y, 40, 20),
                "1e5",
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            )
        painter.drawText(
            canvas.rect(),
            self.x,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
        )
        painter.end()
        self.x_axis.setPixmap(canvas)
        self.x_axis.update()

    def draw_y_axis(self):
        canvas = self.y_axis.pixmap()
        canvas.fill("#121010")
        painter = QPainter(canvas)
        pen = QPen()
        pen.setColor("#bababa")
        painter.setPen(pen)
        painter.drawLine(QPoint(55, 0), QPoint(55, RESOLUTION - 1))
        if self.y in LINEAR_PARAMETERS:
            painter.drawLine(QPoint(51, RESOLUTION - 1), QPoint(55, RESOLUTION - 1))
            painter.drawText(
                QRect(8, 238, 40, 20),
                "0",
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            )
            painter.drawLine(QPoint(51, 205), QPoint(55, 205))
            # painter.drawText(
            #     QRect(8, 193, 40, 20),
            #     "0.5e6",
            #     Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            # )
            painter.drawLine(QPoint(51, 155), QPoint(55, 155))
            painter.drawText(
                QRect(8, 143, 40, 20),
                "1e6",
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            )
            painter.drawLine(QPoint(51, 105), QPoint(55, 105))
            # painter.drawText(
            #     QRect(8, 93, 40, 20),
            #     "1.5e6",
            #     Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            # )
            painter.drawLine(QPoint(51, 55), QPoint(55, 55))
            painter.drawText(
                QRect(8, 43, 40, 20),
                "2e6",
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            )
            painter.drawLine(QPoint(51, 5), QPoint(55, 5))
            # painter.drawText(
            #     QRect(8, -7, 40, 20),
            #     "2.5e6",
            #     Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            # )
        else:
            painter.drawLine(QPoint(51, RESOLUTION - 234), QPoint(55, RESOLUTION - 234))
            painter.drawText(
                QRect(8, RESOLUTION - 242, 40, 40),
                "1e5",
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
            )
            painter.drawLine(QPoint(51, RESOLUTION - 168), QPoint(55, RESOLUTION - 168))
            painter.drawText(
                QRect(8, RESOLUTION - 176, 40, 40),
                "1e4",
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
            )
            painter.drawLine(QPoint(51, RESOLUTION - 103), QPoint(55, RESOLUTION - 103))
            painter.drawText(
                QRect(8, RESOLUTION - 111, 40, 40),
                "1e3",
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
            )
            painter.drawLine(QPoint(51, RESOLUTION - 47), QPoint(55, RESOLUTION - 47))
            painter.drawLine(QPoint(51, RESOLUTION - 29), QPoint(55, RESOLUTION - 29))
            painter.drawText(
                QRect(8, RESOLUTION - 37, 40, 40),
                "0",
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
            )
            painter.drawLine(QPoint(51, RESOLUTION - 11), QPoint(55, RESOLUTION - 11))
        painter.translate(0, 256)
        painter.rotate(-90)
        painter.drawText(
            QRect(0, 0, 255, 20),
            self.y,
            Qt.AlignmentFlag.AlignLeft,
        )
        painter.end()

        self.y_axis.setPixmap(canvas)
        self.y_axis.update()

    def y_context_menu(self, pos):
        menu = QMenu()
        menu.addAction("CD45 AF700")
        menu.addAction("SSC-A")
        menu.addAction("CD19")

        action = menu.exec(self.y_axis.mapToGlobal(pos))
        if action:
            self.y = action.text()
            self.dot_plot()

    def x_context_menu(self, pos):
        menu = QMenu()
        menu.addAction("FSC-A")
        menu.addAction("SSC-A")
        menu.addAction("CD5 BV480")

        action = menu.exec(self.x_axis.mapToGlobal(pos))
        if action:
            self.x = action.text()
            self.dot_plot()


app = QApplication(sys.argv)
window = MainWindow()
window.show()

app.exec()
