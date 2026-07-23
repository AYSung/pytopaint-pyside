# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.
from itertools import chain

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QGroupBox,
    QPushButton,
    QVBoxLayout,
)

from pytopaint.flowdata import PHYSICAL_PARAMETERS, FlowData, sort_channels


class ReportTemplateDialog(QDialog):
    def __init__(self, tubes: list[FlowData], parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        self.tubes = tubes

        groupbox = QGroupBox('Tubes to include:')
        group_layout = QVBoxLayout()
        self.checkboxes = [QCheckBox(tube_data.id) for tube_data in tubes]
        for checkbox in self.checkboxes:
            checkbox.setChecked(True)
            group_layout.addWidget(checkbox)
        groupbox.setLayout(group_layout)
        layout.addWidget(groupbox)

        copy_button = QPushButton('Copy Report Template', self)
        copy_button.setFixedWidth(200)
        copy_button.clicked.connect(self.copy_clicked)
        layout.addWidget(copy_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

    def copy_clicked(self):
        checked_channels = [
            tube_data.fluoro_channels
            for checkbox, tube_data in zip(self.checkboxes, self.tubes)
            if checkbox.isChecked()
        ]

        sorted_channels = sort_channels(set(chain(*checked_channels)))
        copy_report_template(sorted_channels)
        self.accept()


def copy_report_template(channels: list[str]) -> None:
    clipboard = QApplication.clipboard()
    clipboard.setText(generate_report_template(channels))


def generate_report_template(ip_channels: list[str]) -> str:
    immunophenotype_markers = [
        _add_marker_smartlist(channel)
        for channel in ip_channels
        if channel not in PHYSICAL_PARAMETERS
    ]

    template = f"""{_join_list(immunophenotype_markers)}"""

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
