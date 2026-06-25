# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

import shutil
from importlib import resources

from platformdirs import user_config_path

default_config_file = resources.files('pytopaint.resources').joinpath('config.yml')
default_layout_dir = resources.files('pytopaint.resources').joinpath('layouts/')

config_dir = user_config_path(appname='PytoPaint', ensure_exists=True)
config_file = config_dir / 'config.yml'

layout_dir = config_dir / 'layouts'
layout_dir.mkdir(parents=True, exist_ok=True)

if not config_file.exists():
    shutil.copy(src=default_config_file, dst=config_file)

if not any(layout_dir.iterdir()):
    shutil.copytree(src=default_layout_dir, dst=layout_dir, dirs_exist_ok=True)
