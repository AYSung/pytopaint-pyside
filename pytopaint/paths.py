# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

import shutil
from importlib import resources

from platformdirs import user_config_path

default_layout_dir = resources.files('pytopaint.resources').joinpath('layouts/')

config_dir = user_config_path(appname='PytoPaint', ensure_exists=True)

layout_dir = config_dir / 'layouts'
layout_dir.mkdir(parents=True, exist_ok=True)


if not any(layout_dir.iterdir()):
    shutil.copytree(src=default_layout_dir, dst=layout_dir, dirs_exist_ok=True)
else:
    user_layout_filenames = [
        entry.name for entry in layout_dir.iterdir() if entry.is_file()
    ]
    missing_layout_files = [
        entry
        for entry in default_layout_dir.iterdir()
        if entry.is_file() and entry.name not in user_layout_filenames
    ]
    for layout_file in missing_layout_files:
        shutil.copy(src=layout_file, dst=layout_dir)
