# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.


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
        state: pd.DataFrame,
        axis_ticks: dict[str, list[tuple[int, str]]],
        color: Color,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle('Immunophenotyper')

        channels = sort_channels(get_ip_channels(df.columns))
        df = df.join(state[['color']]).loc[state[['visible']]].astype('uint8')
        df = (
            self
            .df[[self.x_axis.label, self.y_axis.label]]
            .loc[self.state['visible']]
            .join(self.state[['color']])
            .drop_duplicates()
        )

        self.percent = (
            state['color'].loc[lambda s: s == color] / state['visible'].sum()
            if state['visible'].any()
            else 0
        )

        layout = QVBoxLayout()
        ip_layout = QHBoxLayout()
        ip_layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        ip_layout.setSpacing(20)
        ROWS_PER_COLUMN = 6
        columns = batched(channels, ROWS_PER_COLUMN)
        for column in columns:
            column_layout = QVBoxLayout()
            column_layout.setSpacing(0)
            for channel in column:
                column_layout.addWidget(
                    immunophenotype_plot(
                        data=df[[channel, 'color']],
                        channel=channel,
                        target_color=color,
                        axis_ticks=axis_ticks,
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
        clipboard.setText(generate_report_template(self.channels, self.percent))


def generate_report_template(ip_channels: list[str], percent_events: float) -> str:
    immunophenotype_markers = [
        _add_marker_smartlist(channel)
        for channel in ip_channels
        if channel not in PHYSICAL_PARAMETERS
    ]

    template = f"""Immunophenotypic analysis reveals a population of {{cell lineage selection:40658}} cells ({_format_percent(percent_events)} of total events) with {{light scatter strength:40657}} forward light scatter, {{light scatter strength:40657}} orthogonal light scatter, and the following immunophenotype: {_join_list(immunophenotype_markers)}"""

    return template


def _add_marker_smartlist(channel) -> str:
    if channel in ['Kappa', 'Lambda']:
        return f'{{surface/IC:46754}} {channel.lower()} light chain ({{+/-:40630}})'
    return f'{channel} ({{+/-:40630}})'


def _join_list(_list: list[str]) -> str:
    if len(_list) <= 2:
        return ' and '.join(_list)
    else:
        return f'{", ".join(_list[:-1])}, and {_list[-1]}'


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


def get_ip_channels(channels: list[str]) -> list[str]:
    return [
        channel
        for channel in channels
        if channel not in ['FSC-H', 'SSC-H', 'Time'] + ADDED_PARAMETERS
    ]
