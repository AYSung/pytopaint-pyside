# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.


from itertools import batched

import anndata as ad
import pandas as pd
from PySide6.QtCore import QLine, QPoint, QRect, Qt
from PySide6.QtGui import QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QVBoxLayout,
    QWidget,
)

from pytopaint.colors import BACKGROUND, Color, get_color_map
from pytopaint.config import get_resolution
from pytopaint.flowdata import PHYSICAL_PARAMETERS, sort_channels


class Immunophenotyper(QDialog):
    def __init__(
        self,
        data: ad.AnnData,
        state: pd.DataFrame,
        color: Color,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle('Immunophenotyper')

        self.channels = sort_channels(
            ['FSC-A', 'SSC-A']
            + data.var_names[data.var['channel_type'] == 'fluoro'].to_list()
        )
        axis_ticks = data.uns['axis_ticks']

        df = (
            pd
            .DataFrame(data.layers['bin'], columns=data.var_names)
            .join(state[['color']])
            .astype('uint8')
            .loc[state['visible']]
        )

        layout = QVBoxLayout()
        layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        ip_layout = QHBoxLayout()
        ip_layout.setSpacing(20)
        ROWS_PER_COLUMN = 6
        columns = batched(self.channels, ROWS_PER_COLUMN)
        for column in columns:
            column_layout = QVBoxLayout()
            column_layout.setSpacing(0)
            for channel in column:
                column_layout.addWidget(
                    immunophenotype_plot(
                        data=df[[channel, 'color']],
                        channel=channel,
                        target_color=color,
                        axis_ticks=axis_ticks[channel],
                    )
                )
            column_layout.addStretch()
            ip_layout.addLayout(column_layout)
        layout.addLayout(ip_layout)
        self.setLayout(layout)


def immunophenotype_plot(
    data: pd.DataFrame,
    channel: str,
    target_color: Color,
    axis_ticks: list[tuple[int, str]],
) -> QWidget:
    plot = QWidget()
    layout = QGridLayout()
    layout.setSpacing(0)
    layout.setContentsMargins(0, 0, 0, 6)
    channel_label = QLabel(channel)
    channel_label.setStyleSheet('font-weight: bold; margin-bottom: 6px;')

    layout.addWidget(channel_label, 0, 0)
    layout.addWidget(histogram(data=data, target_color=target_color), 1, 0)
    layout.addWidget(histogram_axis(channel, axis_ticks), 2, 0)

    plot.setLayout(layout)
    return plot


def histogram(data: pd.DataFrame, target_color: Color) -> QLabel:
    histogram = QLabel()
    MAX_HEIGHT = 9

    canvas = QPixmap(get_resolution(), 40)
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


def histogram_axis(channel: str, axis_ticks: list[tuple[int, str]]) -> QLabel:
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
