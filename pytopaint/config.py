# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

from dataclasses import asdict, dataclass

import yaml

from pytopaint.paths import config_file


@dataclass
class AppConfig:
    resolution: int
    scaling_factor: int
    upper_arcsinh_limit: float
    lower_arcsinh_limit: float


def import_config() -> AppConfig:
    with open(config_file) as stream:
        config = yaml.safe_load(stream)

    return AppConfig(**config)


appconfig = import_config()


def save_config() -> None:
    with open(config_file, 'w') as handle:
        yaml.safe_dump(
            asdict(appconfig),
            handle,
            default_flow_style=False,
            sort_keys=False,
            explicit_start=True,
        )
