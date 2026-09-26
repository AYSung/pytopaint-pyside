# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.


import os
import shutil
from importlib import resources
from pathlib import Path

from platformdirs import user_config_path
from PySide6.QtCore import QPoint, QSettings

_default_layout_dir = resources.files('pytopaint.resources').joinpath(
    'painter_layouts/'
)

_config_dir = user_config_path(appname='PytoPaint', ensure_exists=True)
_user_layout_dir = _config_dir / 'layouts'
_user_layout_dir.mkdir(parents=True, exist_ok=True)


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


def get_highlight_size() -> int:
    return int(QSettings().value('Plot/highlight_size', 2))


def set_highlight_size(size: int) -> None:
    QSettings().setValue('Plot/highlight_size', size)


def get_window_position() -> QPoint:
    return QSettings().value('MainWindow/position', QPoint(20, 40))


def set_window_position(pos: QPoint) -> None:
    QSettings().setValue('MainWindow/position', pos)


def get_painter_layout_directory() -> Path:
    path = Path(QSettings().value('Paths/painter_layouts', _user_layout_dir))
    if _is_valid_directory(path) and (path != _default_layout_dir):
        copy_default_layouts(path)
        return path
    else:
        reset_painter_layout_directory()
        return _get_default_layout_dir()


def set_painter_layout_directory(path: Path) -> None:
    copy_default_layouts(path)
    QSettings().setValue('Paths/painter_layouts', str(path))


def reset_painter_layout_directory() -> None:
    QSettings().setValue('Paths/painter_layouts', str(_get_default_layout_dir()))


def _is_valid_directory(path: str | Path) -> bool:
    return (
        os.access(path, os.F_OK)
        and os.access(path, os.R_OK)
        and os.access(path, os.W_OK)
    )


def _get_default_layout_dir() -> Path:
    if _is_valid_directory(_user_layout_dir):
        return _user_layout_dir
    else:
        return _default_layout_dir


def copy_default_layouts(target_dir: Path) -> None:
    if not any(target_dir.iterdir()):
        shutil.copytree(src=_default_layout_dir, dst=target_dir, dirs_exist_ok=True)
    else:
        user_layout_filenames = [
            entry.name for entry in target_dir.iterdir() if entry.is_file()
        ]
        missing_layout_files = [
            entry
            for entry in _default_layout_dir.iterdir()
            if entry.is_file() and entry.name not in user_layout_filenames
        ]
        for layout_file in missing_layout_files:
            shutil.copy(src=layout_file, dst=target_dir)
