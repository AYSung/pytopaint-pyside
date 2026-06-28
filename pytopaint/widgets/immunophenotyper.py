from itertools import batched

import pandas as pd
from PySide6.QtCore import QLine, QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pytopaint.colors import BACKGROUND, Color, get_color_map
from pytopaint.config import get_resolution
from pytopaint.flowdata import ADDED_PARAMETERS, PHYSICAL_PARAMETERS, sort_channels
from pytopaint.widgets.palette import _format_percent


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

        self.channels = get_ip_channels(sort_channels(df.columns))

        self.percent = df.color.loc[df.color == color].size / df.color.size

        layout = QVBoxLayout()
        ip_layout = QHBoxLayout()
        ip_layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        ip_layout.setSpacing(20)
        ROWS_PER_COLUMN = 6
        columns = batched(self.channels, ROWS_PER_COLUMN)
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
            ip_layout.addLayout(column_layout)
        layout.addLayout(ip_layout)

        copy_button = QPushButton('Copy Report Template', self)
        copy_button.setFixedWidth(200)
        copy_button.clicked.connect(lambda: self.copy_clicked(copy_button))
        layout.addWidget(copy_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

    def copy_clicked(self, button: QPushButton) -> None:
        def restore_button():
            button.setEnabled(True)
            button.setText('Copy Report Template')

        self.copy_report_template()
        button.setEnabled(False)
        button.setText('Copied!')
        QTimer.singleShot(2000, restore_button)

    def copy_report_template(self) -> None:
        clipboard = QApplication.clipboard()
        clipboard.setText(self.generate_report_template())

    def generate_report_template(self) -> str:
        def _add_marker_smartlist(channel) -> str:
            if channel in ['Kappa', 'Lambda']:
                return f'{{surface/IC:46754}} {channel.lower()} light chain ({{+/-:40630}})'
            return f'{channel} ({{+/-:40630}})'

        def _join_list(channels: list[str]) -> str:
            if not channels:
                return ''
            elif len(channels) == 1:
                return _add_marker_smartlist(channels[0])
            elif len(channels) == 2:
                return f'{_add_marker_smartlist(channels[0])} and {_add_marker_smartlist(channels[1])}'

            return f'{", ".join(map(_add_marker_smartlist, channels[:-1]))}, and {_add_marker_smartlist(channels[-1])}'

        channels = [
            channel for channel in self.channels if channel not in PHYSICAL_PARAMETERS
        ]

        template = f"""Immunophenotypic analysis reveals a population of {{cell lineage selection:40658}} cells ({_format_percent(self.percent)} of total events) with {{light scatter strength:40657}} forward light scatter, {{light scatter strength:40657}} orthogonal light scatter, and the following immunophenotype: {_join_list(channels)}"""

        return template


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
