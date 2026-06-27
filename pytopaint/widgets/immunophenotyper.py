from itertools import batched
import pandas as pd

from PySide6.QtCore import QPoint, QRect, Qt, QLine
from PySide6.QtGui import QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLayout,
)

from pytopaint.colors import BACKGROUND, get_color_map, Color
from pytopaint.flowdata import PHYSICAL_PARAMETERS, sort_channels, ADDED_PARAMETERS
from pytopaint.config import get_resolution


class Immunophenotyper(QDialog):
    def __init__(
        self,
        df: pd.DataFrame,
        axis_ticks: dict[str, tuple[int, str]],
        color: Color,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle('Immunophenotyper')

        channels = get_ip_channels(sort_channels(df.columns))

        layout = QHBoxLayout()
        layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        layout.setSpacing(20)
        ROWS_PER_COLUMN = 6
        columns = batched(channels, ROWS_PER_COLUMN)
        for column in columns:
            column_layout = QVBoxLayout()
            column_layout.setSpacing(0)
            for channel in column:
                column_layout.addWidget(
                    ImmunophenotypePlot(
                        df=df[[channel, 'color']],
                        channel=channel,
                        axis_ticks=axis_ticks[channel],
                        target_color=color,
                    )
                )
            column_layout
            layout.addLayout(column_layout)
        self.setLayout(layout)


class ImmunophenotypePlot(QWidget):
    def __init__(
        self,
        df: pd.DataFrame,
        channel: str,
        axis_ticks: tuple[int, str],
        target_color: Color,
        parent=None,
    ):
        super().__init__(parent)
        self.channel = channel

        layout = QGridLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 6)
        channel_label = QLabel(channel)
        channel_label.setStyleSheet('font-weight: bold; margin-bottom: 6px;')

        layout.addWidget(channel_label, 0, 0)
        layout.addWidget(
            Histogram(df=df, channel=channel, target_color=target_color), 1, 0
        )
        layout.addWidget(histogram_axis(channel, axis_ticks), 2, 0)

        self.setLayout(layout)


class Histogram(QLabel):
    def __init__(
        self, df: pd.DataFrame, channel: str, target_color: Color, parent=None
    ):
        super().__init__(parent)
        canvas = QPixmap(get_resolution(), 40)
        canvas.fill(BACKGROUND)
        painter = QPainter(canvas)
        self.draw_histogram(painter, df, channel, target_color)
        painter.end()
        self.setPixmap(canvas)

    def draw_histogram(
        self, painter: QPainter, df: pd.DataFrame, channel: str, target_color: Color
    ) -> None:
        pen = QPen()

        painter.translate(0, 10)
        pen.setColor(get_color_map()[target_color])
        painter.setPen(pen)
        painter.drawLines([
            QLine(x, -count, x, count)
            for x, count in to_histogram_values(
                df=df, channel=channel, color=target_color
            )
        ])

        painter.translate(0, 20)
        other_colors = [color for color in Color if color != target_color]
        for color in other_colors:
            pen.setColor(get_color_map()[color])
            painter.setPen(pen)
            painter.drawLines([
                QLine(x, -count, x, count)
                for x, count in to_histogram_values(df=df, channel=channel, color=color)
            ])


def to_histogram_values(
    df: pd.DataFrame, channel: str, color: Color
) -> tuple[int, int]:
    MAX_HEIGHT = 9
    return (
        df
        .loc[df.color == color, channel]
        .value_counts()
        .reset_index()
        .assign(count=lambda x: x['count'] / x['count'].max() * MAX_HEIGHT)
        .to_records(index=False)
    )


def histogram_axis(channel: str, axis_ticks: tuple[int, str]) -> QLabel:
    axis = QLabel()

    canvas = QPixmap(get_resolution(), 20)
    canvas.fill('#00000000')

    painter = QPainter(canvas)
    pen = QPen()
    pen.setColor('#bababa')
    painter.setPen(pen)

    label_y = 6
    tick_y0 = 0
    tick_y1 = tick_y0 + 4
    X_MAX = get_resolution() - 1

    painter.drawLine(QPoint(0, tick_y0), QPoint(X_MAX, tick_y0))

    for tick, _ in axis_ticks:
        painter.drawLine(QPoint(tick, tick_y0), QPoint(tick, tick_y1))

    axis_labels = (
        [(4, '0')] + axis_ticks[1:] if channel in PHYSICAL_PARAMETERS else axis_ticks
    )

    for tick, label in filter(lambda x: x is not None, axis_labels):
        painter.drawText(
            QRect(tick - 20, label_y, 40, 20),
            label,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
        )
    painter.end()

    axis.setPixmap(canvas)
    return axis


def get_ip_channels(channels: list[str]) -> list[str]:
    return [
        channel
        for channel in channels
        if channel not in ['FSC-H', 'SSC-H', 'Time', 'color'] + ADDED_PARAMETERS
    ]
