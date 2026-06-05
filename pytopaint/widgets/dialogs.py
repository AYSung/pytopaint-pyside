import flowkit
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

from pytopaint.config import appconfig
from pytopaint.flowdata import sort_channels


def about_dialog(parent: QWidget) -> None:
    return QMessageBox.about(
        parent,
        'About PytoPaint',
        'PytoPaint v0.1\n\n\nCreated by Andrew Y. Sung\n\nLast updated May 2026',
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
            ('Paint events', 'Left-Click'),
            ('Paint non-grey events', 'Shift + Left-Click'),
            ('Override paint colors', 'Ctrl+Left-Click'),
            ('Override non-grey events', 'Ctrl+Shift+Left-Click'),
        ])
    )
    layout.addWidget(
        _shortcut_table([
            ('Exact zap from selection', 'Right-Click'),
            ('Zap from selection', 'Shift + Right-Click'),
            ('Paint grey', 'Ctrl+Right-Click'),
        ])
    )
    layout.addWidget(
        _shortcut_table([
            ('Exact zap color', 'Middle-Click'),
            ('Zap color', 'Shift + Middle-Click'),
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
            ('Hide Current Color', 'Backspace'),
            ('Isolate Current Color', 'Enter'),
            ('Reset Events', 'Ctrl + R'),
            ('Open File(s)', 'Ctrl + O'),
            ('Close Tab', 'Ctrl + W'),
            ('Close Application', 'Ctrl + Q'),
        ])
    )

    layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

    dialog.setLayout(layout)

    return dialog


class PlotScaleDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Scale')
        field_width = 60

        layout = QFormLayout()
        layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        self.scaling_factor_input = QSpinBox(singleStep=10)
        self.scaling_factor_input.setRange(20, 1200)
        self.scaling_factor_input.setValue(appconfig.scaling_factor)
        self.scaling_factor_input.setFixedWidth(field_width)
        self.scaling_factor_input.setToolTip('between 20 and 1200')
        self.upper_arcsinh_limit_input = QDoubleSpinBox(singleStep=0.5)
        self.upper_arcsinh_limit_input.setRange(5, 15)
        self.upper_arcsinh_limit_input.setValue(appconfig.upper_arcsinh_limit)
        self.upper_arcsinh_limit_input.setFixedWidth(field_width)
        self.upper_arcsinh_limit_input.setToolTip('between 5 and 15')
        self.lower_arcsinh_limit_input = QDoubleSpinBox(singleStep=0.5)
        self.lower_arcsinh_limit_input.setRange(-5, 4)
        self.lower_arcsinh_limit_input.setValue(appconfig.lower_arcsinh_limit)
        self.lower_arcsinh_limit_input.setFixedWidth(field_width)
        self.lower_arcsinh_limit_input.setToolTip('between -5 and 4')
        layout.addRow('Scaling Factor:', self.scaling_factor_input)
        layout.addRow('Upper Bound:', self.upper_arcsinh_limit_input)
        layout.addRow('Lower Bound:', self.lower_arcsinh_limit_input)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)

        self.setLayout(layout)

    @property
    def scaling_factor(self) -> int:
        return self.scaling_factor_input.value()

    @property
    def upper_arcsinh_limit(self) -> float:
        return self.upper_arcsinh_limit_input.value()

    @property
    def lower_arcsinh_limit(self) -> float:
        return self.lower_arcsinh_limit_input.value()


def file_info_dialog(parent: QWidget, sample: flowkit.Sample) -> QDialog:
    dialog = QDialog(parent)
    dialog.setWindowTitle('File Info')

    file_name = QLabel(f'File Name: {sample.current_filename}')
    event_count = QLabel(f'Event Count: {sample.event_count:,}')
    channels = [
        f'{marker} ({fluor})' if marker else fluor
        for fluor, marker in sample.channels[['pnn', 'pns']].to_records(index=False)
    ]
    channels_label = QLabel(f'Channels: \n{"\n".join(sort_channels(channels))}')

    button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
    button_box.accepted.connect(dialog.accept)

    layout = QVBoxLayout()
    layout.addWidget(file_name)
    layout.addWidget(event_count)
    layout.addWidget(channels_label)
    layout.addWidget(button_box)
    layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

    dialog.setLayout(layout)

    return dialog


def save_config_dialog(parent: QWidget) -> bool:
    reply = QMessageBox().question(
        parent,
        'Confirm',
        'Save changes to configuration?',
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )

    return reply == QMessageBox.StandardButton.Yes


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


def resize_plot_dialog(parent: QWidget) -> tuple[int, bool]:
    return QInputDialog.getInt(
        parent,
        'Size',
        'Pixels per dimension (128-256)',
        value=appconfig.resolution,
        minValue=128,
        maxValue=256,
        step=16,
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
