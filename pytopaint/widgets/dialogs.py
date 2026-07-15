# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

import anndata as ad
from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QInputDialog,
    QLabel,
    QLayout,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pytopaint.config import (
    get_lower_asinh_bound,
    get_resolution,
    get_scaling_factor,
    get_upper_asinh_bound,
    set_lower_asinh_bound,
    set_scaling_factor,
    set_upper_asinh_bound,
)
from pytopaint.flowdata import sort_channels
from pytopaint.widgets.reportgenerator import ReportTemplateDialog


def about_dialog(parent: QWidget) -> None:
    return QMessageBox.about(
        parent,
        'About PytoPaint',
        'PytoPaint v0.3.2 (pre-release)\n\n\nCreated by Andrew Y. Sung\n\nLast updated July 2026\n\nFor research and educational use only.',
    )


def shortcut_dialog(parent: QWidget) -> QDialog:
    def _shortcut_table(shortcuts: list[tuple[str, str]]) -> QWidget:
        table = QWidget()
        grid = QGridLayout()
        grid.setColumnMinimumWidth(0, 200)
        for row, (function, shortcut) in enumerate(shortcuts):
            grid.addWidget(QLabel(function), row, 0)
            grid.addWidget(QLabel(shortcut), row, 1)
        table.setLayout(grid)
        return table

    def _hline() -> QFrame:
        hline = QFrame()
        hline.setFrameShape(QFrame.Shape.HLine)
        return hline

    dialog = QDialog(parent)
    dialog.setWindowTitle('Shortcuts')

    layout = QVBoxLayout()
    layout.addWidget(QLabel('<b>Mouse Controls (within biplots):</b>'))
    layout.addWidget(
        _shortcut_table([
            ('Paint Events', 'Left-Click'),
            ('Paint Non-Grey Events', 'Shift + Left-Click'),
            ('Paint Grey Events', 'Ctrl + Left-Click'),
            ('Override Paint Colors', 'Ctrl + Shift + Left-Click'),
        ])
    )
    layout.addWidget(
        _shortcut_table([
            ('Exact Zap from Selection', 'Right-Click'),
            ('Zap from Selection', 'Shift + Right-Click'),
            ('Paint Grey', 'Ctrl + Right-Click'),
        ])
    )
    layout.addWidget(
        _shortcut_table([
            ('Exact Zap Current Color', 'Middle-Click'),
            ('Zap Current Color', 'Shift + Middle-Click'),
            ('Zap All', 'Ctrl + Middle-Click'),
        ])
    )
    layout.addWidget(_hline())

    layout.addWidget(QLabel('<b>Keyboard Controls:</b>'))
    layout.addWidget(
        _shortcut_table([
            ('Undo', 'Ctrl + Z'),
            ('Redo', 'Ctrl + Shift + Z'),
            ('Paint Red', 'F'),
            ('Paint Green', 'D'),
            ('Paint Blue', 'S'),
            ('Paint Cyan', 'Shift + F'),
            ('Paint Magenta', 'Shift + D'),
            ('Paint Yellow', 'Shift + S'),
            ('Paint White', 'A'),
            ('Exact Zap Current Color', 'E'),
            ('Zap Current Color', 'Ctrl + E'),
            ('Zap All', 'Ctrl + Shift + E'),
            ('Hide Current Color', 'Backspace'),
            ('Isolate Current Color', 'Enter'),
            ('Unhide Events', 'Ctrl + R'),
            ('Reset Events', 'Ctrl + Shift + R'),
            ('Open File(s)', 'Ctrl + O'),
            ('Load Layout', 'Ctrl + L'),
            ('Close Current Tab', 'Ctrl + W'),
            ('Close All Tabs', 'Ctrl + Shift + W'),
            ('Close Application', 'Ctrl + Q'),
        ])
    )

    layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

    dialog.setLayout(layout)

    return dialog


class PlotScaleDialog(QDialog):
    def __init__(
        self,
        scaling_factor: float,
        lower_asinh_bound: float,
        upper_asinh_bound: float,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle('Plot Scale')
        field_width = 60

        layout = QFormLayout()
        layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        self.scaling_factor_input = QSpinBox(singleStep=10)
        self.scaling_factor_input.setRange(20, 1200)
        self.scaling_factor_input.setValue(scaling_factor)
        self.scaling_factor_input.setFixedWidth(field_width)
        self.scaling_factor_input.setToolTip('between 20 and 1200')
        self.upper_asinh_bound_input = QDoubleSpinBox(singleStep=0.5)
        self.upper_asinh_bound_input.setRange(5, 15)
        self.upper_asinh_bound_input.setValue(upper_asinh_bound)
        self.upper_asinh_bound_input.setFixedWidth(field_width)
        self.upper_asinh_bound_input.setToolTip('between 5 and 15')
        self.lower_asinh_bound_input = QDoubleSpinBox(singleStep=0.5)
        self.lower_asinh_bound_input.setRange(-5, 4)
        self.lower_asinh_bound_input.setValue(lower_asinh_bound)
        self.lower_asinh_bound_input.setFixedWidth(field_width)
        self.lower_asinh_bound_input.setToolTip('between -5 and 4')
        layout.addRow('Scaling Factor:', self.scaling_factor_input)
        layout.addRow('Upper Bound:', self.upper_asinh_bound_input)
        layout.addRow('Lower Bound:', self.lower_asinh_bound_input)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        save_defaults_btn = button_box.addButton(
            'Save as Default', QDialogButtonBox.ButtonRole.ActionRole
        )
        save_defaults_btn.clicked.connect(self.save_defaults)
        reset_to_defaults_btn = button_box.addButton(
            'Reset', QDialogButtonBox.ButtonRole.ActionRole
        )
        reset_to_defaults_btn.clicked.connect(self.reset_to_defaults)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)

        self.setLayout(layout)

    @Slot()
    def reset_to_defaults(self) -> None:
        self.scaling_factor_input.setValue(get_scaling_factor())
        self.upper_asinh_bound_input.setValue(get_upper_asinh_bound())
        self.lower_asinh_bound_input.setValue(get_lower_asinh_bound())

    @Slot()
    def save_defaults(self) -> None:
        set_scaling_factor(self.scaling_factor)
        set_lower_asinh_bound(self.lower_asinh_bound)
        set_upper_asinh_bound(self.upper_asinh_bound)

    @property
    def scaling_factor(self) -> int:
        return self.scaling_factor_input.value()

    @property
    def upper_asinh_bound(self) -> float:
        return self.upper_asinh_bound_input.value()

    @property
    def lower_asinh_bound(self) -> float:
        return self.lower_asinh_bound_input.value()

    @property
    def scale_config(self) -> dict[str, float]:
        return {
            'scaling_factor': self.scaling_factor,
            'lower_asinh_bound': self.lower_asinh_bound,
            'upper_asinh_bound': self.upper_asinh_bound,
        }


def resize_plot_dialog(parent: QWidget) -> tuple[int, bool]:
    return QInputDialog.getInt(
        parent,
        'Size',
        'Pixels per dimension (128-512)',
        value=get_resolution(),
        minValue=128,
        maxValue=512,
        step=16,
    )


def file_info_dialog(parent: QWidget, data: ad.AnnData) -> QDialog:
    dialog = QDialog(parent)
    dialog.setWindowTitle('File Info')

    file_name = QLabel(f'File Name: {data.uns["filename"]}')
    event_count = QLabel(f'Event Count: {data.n_obs:,}')
    channels = [
        f'{marker} ({fluor})'
        for fluor, marker in data.var.loc[
            data.var['channel_type'] == 'fluoro', ['pnn_label', 'pns_label']
        ].to_records(index=False)
    ]
    channels_label = QLabel(f'Channels: \n{"\n".join(sort_channels(channels))}')

    button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
    button_box.accepted.connect(dialog.accept)

    layout = QVBoxLayout()
    layout.addWidget(file_name)
    if (tube := data.uns.get('tube')) is not None:
        tube_label = QLabel(f'Tube: {tube}')
        layout.addWidget(tube_label)
    layout.addWidget(event_count)
    layout.addWidget(channels_label)
    layout.addWidget(button_box)
    layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

    dialog.setLayout(layout)

    return dialog


def subsample_dialog(parent: QWidget, total_events: int) -> tuple[int, bool]:
    return QInputDialog.getInt(
        parent,
        'Subsample Events',
        'Events to subsample (min. 1000):',
        value=min(10_000, total_events),
        minValue=1_000,
        maxValue=total_events,
        step=1_000,
    )


def add_row_dialog(parent: QWidget) -> tuple[int, bool]:
    return QInputDialog.getInt(
        parent,
        'Add Rows',
        'Number of Rows',
        value=1,
        minValue=1,
        maxValue=10,
    )


def add_column_dialog(parent: QWidget) -> tuple[int, bool]:
    return QInputDialog.getInt(
        parent,
        'Add Columns',
        'Number of Columns',
        value=1,
        minValue=1,
        maxValue=10,
    )


def report_generator_dialog(parent: QWidget, tubes: list[ad.AnnData]) -> int:
    report_generator = ReportTemplateDialog(tubes, parent)

    return report_generator.exec()
