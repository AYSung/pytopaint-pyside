# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.


from PySide6.QtCore import QPoint, QSettings


def get_color_palette() -> str:
    return QSettings().value('Plot/color_palette', 'Default')


def set_color_palette(palette: str) -> None:
    QSettings().setValue('Plot/color_palette', palette)


def get_resolution() -> int:
    return int(QSettings().value('Plot/resolution', 208))


def set_resolution(pixels: int) -> None:
    QSettings().setValue('Plot/resolution', pixels)


def get_zoom_resolution() -> int:
    return int(QSettings().value('Plot/zoom_resolution', 512))


def set_zoom_resolution(pixels: int) -> None:
    QSettings().setValue('Plot/zoom_resolution', pixels)


def get_scaling_factor() -> float:
    return float(QSettings().value('Plot/scaling_factor', 150))


def set_scaling_factor(scaling_factor: float) -> None:
    QSettings().setValue('Plot/scaling_factor', scaling_factor)


def get_upper_asinh_bound() -> float:
    return float(QSettings().value('Plot/upper_asinh_bound', 8))


def set_upper_asinh_bound(bound: float) -> None:
    QSettings().setValue('Plot/upper_asinh_bound', bound)


def get_lower_asinh_bound() -> float:
    return float(QSettings().value('Plot/lower_asinh_bound', -1))


def set_lower_asinh_bound(bound: float) -> None:
    QSettings().setValue('Plot/lower_asinh_bound', bound)


def get_window_position() -> QPoint:
    return QSettings().value('MainWindow/position', QPoint(20, 40))


def set_window_position(pos: QPoint) -> None:
    QSettings().setValue('MainWindow/position', pos)
