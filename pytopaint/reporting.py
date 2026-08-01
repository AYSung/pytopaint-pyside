# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

from importlib import resources
from itertools import chain
from pathlib import Path

import pandas as pd
import yaml
from PySide6.QtCore import QDateTime
from PySide6.QtGui import (
    QPageSize,
    QPainter,
    QPdfWriter,
    QTextDocument,
)

from pytopaint.channels import PHYSICAL_PARAMETERS, sort_channels
from pytopaint.colors import Color, events_by_color
from pytopaint.flowdata import discretize_data, get_axis_ticks
from pytopaint.widgets.biplot import Biplot
from pytopaint.widgets.painter import Painter

GRID_SIZE = 300
X_OFFSET = 30
Y_OFFSET = 75
GRID_COORDS = [
    (X_OFFSET + (GRID_SIZE * i), Y_OFFSET + (GRID_SIZE * j))
    for j in range(6)
    for i in range(4)
    if (i, j) != (3, 0)
]
PLOT_RESOLUTION = 224

type ReportLayout = list[tuple[str, str]]


def generate_pdf(file_path: str, tubes: list[Painter]) -> None:
    writer = QPdfWriter(file_path)
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.Letter))  # 1275 x 1650 pixels

    writer.setResolution(150)

    painter = QPainter(writer)

    for i, tube in enumerate(tubes):
        if i > 0:
            writer.newPage()

        # report header
        header_coords = (X_OFFSET, X_OFFSET)
        datetime = QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm')
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        painter.drawText(
            *header_coords,
            f'File: {tube.data.adata.uns.get("filename", tube.data.id)}; analyzed {datetime}',
        )

        biplot_channels = get_report_layout(tube.data.channels)

        painter.save()

        color_legend_coords = (X_OFFSET + (GRID_SIZE * 3) + 35, Y_OFFSET - 10)
        color_legend = draw_color_legend(tube.state)
        painter.translate(*color_legend_coords)
        painter.scale(1.5, 1.5)
        color_legend.drawContents(painter)

        painter.restore()

        binned_df = pd.DataFrame(
            discretize_data(tube.data.adata, bins=PLOT_RESOLUTION),
            columns=tube.data.adata.var_names,
        )
        axis_ticks = get_axis_ticks(tube.data.adata, bins=PLOT_RESOLUTION)

        biplot = Biplot(
            data=binned_df,
            axis_ticks=axis_ticks,
            state=tube.state,
            x_channel=None,
            y_channel=None,
            active_color=Color.BLUE,
            resolution=PLOT_RESOLUTION,
            highlighted_colors=tube.highlighted_colors,
            channel_fluor_map=tube.data.channel_fluor_map,
        )

        # limited to 19 plots per page
        for coords, channels in zip(GRID_COORDS, biplot_channels):
            x_channel, y_channel = channels
            biplot.set_axes(x_channel, y_channel)
            biplot.x_axis.label = tube.data.channel_fluor_map.get(x_channel, x_channel)
            biplot.y_axis.label = tube.data.channel_fluor_map.get(y_channel, y_channel)
            painter.drawImage(*coords, biplot._draw_plot('report'))

    painter.end()


def draw_color_legend(state: pd.DataFrame) -> QTextDocument:
    color_legend = QTextDocument()

    events = events_by_color(state.loc[state['visible'], 'color'])
    total_events = state['visible'].sum()

    color_legend.setHtml(f"""<b style='color:black;'>Color Legend:</b>
    <table style='color: black;'>
        <tr>
            <td style='color: #ff0000;'>Red:</td>
            <td style='text-align: right; padding-left: 20px'>{events.get(Color.RED, 0) / total_events:.2%}</td>
        </tr>
        <tr>
            <td style='color: #00ff00;'>Green:</td>
            <td style='text-align: right; padding-left: 20px'>{events.get(Color.GREEN, 0) / total_events:.2%}</td>
        </tr>
        <tr>
            <td style='color: #0000ff;'>Blue:</td>
            <td style='text-align: right; padding-left: 20px'>{events.get(Color.BLUE, 0) / total_events:.2%}</td>
        </tr>
        <tr>
            <td style='color: #ffbf00;'>Yellow:</td>
            <td style='text-align: right; padding-left: 20px'>{events.get(Color.YELLOW, 0) / total_events:.2%}</td>
        </tr>
        <tr>
            <td style='color: #00ffff;'>Cyan:</td>
            <td style='text-align: right; padding-left: 20px'>{events.get(Color.CYAN, 0) / total_events:.2%}</td>
        </tr>
        <tr>
            <td style='color: #ff00ff;'>Magenta:</td>
            <td style='text-align: right; padding-left: 20px'>{events.get(Color.MAGENTA, 0) / total_events:.2%}</td>
        </tr>
        <tr>
            <td>White:</td>
            <td style='text-align: right; padding-left: 20px'>{events.get(Color.WHITE, 0) / total_events:.2%}</td>
        </tr>
        <tr>
            <td style='color: #8f8f8f;'>Unclassified:</td>
            <td style='text-align: right; padding-left: 20px'>{events.get(Color.GREY, 0) / total_events:.2%}</td>
        </tr>
    </table>
    """)
    return color_legend


def get_report_layout(data_channels: list[str]) -> ReportLayout:
    def _score_layout(layout: ReportLayout) -> float:
        overlap = len(set(chain(*layout)).intersection(set(data_channels)))
        layout_score = overlap / len(layout)
        channel_score = overlap / len(data_channels)
        return layout_score * channel_score

    def _replace_channels(channels: tuple[str, str]) -> tuple[str, str]:
        x_channel, y_channel = channels
        if x_channel in unused_channel_map:
            x_channel = unused_channel_map[x_channel]
        if y_channel in unused_channel_map:
            y_channel = unused_channel_map[y_channel]
        return x_channel, y_channel

    def _is_in_data(channels: tuple[str, str]) -> bool:
        x_channel, y_channel = channels
        return x_channel in data_channels and y_channel in data_channels

    best_layout = max(import_report_layouts(), key=_score_layout)

    layout_channels = set(chain(*best_layout)) | set(PHYSICAL_PARAMETERS + ['Time'])
    unused_layout_channels = sort_channels(
        layout_channels.difference(set(data_channels))
    )
    unused_data_channels = sort_channels(set(data_channels).difference(layout_channels))
    unused_channel_map = dict(zip(unused_layout_channels, unused_data_channels))

    return list(filter(_is_in_data, map(_replace_channels, best_layout)))


def _import_report_layout(path: Path) -> ReportLayout:
    with open(path) as stream:
        return list(map(tuple, yaml.safe_load(stream)))


def import_report_layouts() -> list[ReportLayout]:
    dir = resources.files('pytopaint.resources.report_layouts')

    return [
        _import_report_layout(item)
        for item in dir.iterdir()
        if item.is_file()
        and item.name.endswith('.yml')
        and not item.name.startswith('.')
    ]
