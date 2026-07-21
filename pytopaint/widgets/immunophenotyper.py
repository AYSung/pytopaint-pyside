# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.


from itertools import batched

import pandas as pd
from PySide6.QtCore import QLine, QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
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
from pytopaint.flowdata import PHYSICAL_PARAMETERS, FlowData
from pytopaint.widgets.reportgenerator import copy_report_template


class Immunophenotyper(QDialog):
    def __init__(
        self,
        data: FlowData,
        state: pd.DataFrame,
        color: Color,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle('Immunophenotyper')
        self.setStyleSheet(
            '.QDialog {background-color: #333333} QLabel {color: #bababa}'
        )

        self.channels = ['FSC-A', 'SSC-A'] + data.fluoro_channels

        df = data.binned_df.join(state[['color']]).loc[state['visible']]

        self.percent = (
            state['color'].loc[state['visible'] & (state['color'] == color)].size
            / state['visible'].sum()
        )

        layout = QVBoxLayout()
        layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        ip_layout = QHBoxLayout()
        ip_layout.setSpacing(20)
        ROWS_PER_COLUMN = 6
        columns = batched(self.channels, ROWS_PER_COLUMN)
        for column in columns:
            column_layout = QVBoxLayout()
            column_layout.setSpacing(5)
            for channel in column:
                column_layout.addWidget(
                    immunophenotype_plot(
                        data=df[[channel, 'color']],
                        channel=channel,
                        target_color=color,
                        axis_ticks=data.axis_ticks[channel],
                        resolution=get_resolution(),
                    )
                )
            column_layout.addStretch()
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

        copy_report_template(self.channels, self.percent)
        button.setEnabled(False)
        button.setText('Copied!')
        QTimer.singleShot(2000, restore_button)


def immunophenotype_plot(
    data: pd.DataFrame,
    channel: str,
    target_color: Color,
    axis_ticks: list[tuple[int, str]],
    resolution: int,
) -> QWidget:
    plot = QWidget()
    layout = QGridLayout()
    layout.setSpacing(0)
    layout.setContentsMargins(0, 0, 0, 6)
    channel_label = QLabel(channel)
    channel_label.setStyleSheet('font-weight: bold; margin-bottom: 6px;')

    layout.addWidget(channel_label, 0, 0)
    layout.addWidget(
        histogram(data=data, target_color=target_color, resolution=resolution), 1, 0
    )
    layout.addWidget(histogram_axis(channel, axis_ticks, resolution=resolution), 2, 0)

    plot.setLayout(layout)
    return plot


def histogram(data: pd.DataFrame, target_color: Color, resolution: int) -> QLabel:
    histogram = QLabel()
    MAX_HEIGHT = 9

    canvas = QPixmap(resolution, 40)
    canvas.fill(BACKGROUND)
    painter = QPainter(canvas)
    pen = QPen()

    df = (
        data
        .groupby('color')
        .value_counts()
        .groupby('color')
        .transform(lambda x: x / x.max() * MAX_HEIGHT)
        .reset_index()
        .groupby('color')
    )

    painter.translate(0, 10)
    pen.setColor(get_color_map()[target_color])
    painter.setPen(pen)
    painter.drawLines([
        QLine(x, -count, x, count)
        for x, count in df
        .get_group(target_color)
        .drop(columns='color')
        .to_records(index=False)
    ])

    painter.translate(0, 20)
    other_colors = [color for color in data['color'].unique() if color != target_color]
    for color in other_colors:
        pen.setColor(get_color_map()[color])
        painter.setPen(pen)
        painter.drawLines([
            QLine(x, -count, x, count)
            for x, count in df
            .get_group(color)
            .drop(columns='color')
            .to_records(index=False)
        ])

    painter.end()
    histogram.setPixmap(canvas)
    return histogram


def histogram_axis(
    channel: str, axis_ticks: list[tuple[int, str]], resolution
) -> QLabel:
    axis = QLabel()

    canvas = QPixmap(resolution, 20)
    canvas.fill('#00000000')

    painter = QPainter(canvas)
    pen = QPen()
    pen.setColor('#bababa')
    painter.setPen(pen)

    label_y = 6
    tick_y0 = 0
    tick_y1 = tick_y0 + 4
    X_MAX = resolution - 1

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
