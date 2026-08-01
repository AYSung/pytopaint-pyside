# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

import re
from collections.abc import Iterable

PHYSICAL_PARAMETERS = ['FSC-A', 'FSC-H', 'SSC-A', 'SSC-H']


def sort_channels(channels: Iterable[str]) -> list[str]:
    light_scatter_channels = sorted(
        filter(lambda x: x in PHYSICAL_PARAMETERS, channels)
    )
    cd_channels = sorted(
        [channel for channel in channels if channel.startswith('CD')],
        key=lambda s: int(re.match(r'CD(\d+) ?', s).group(1)),
    )
    non_cd_channels = sorted([
        channel
        for channel in channels
        if not channel.startswith('CD')
        and channel not in PHYSICAL_PARAMETERS + ['Time']
    ])
    time_channel = ['Time'] if 'Time' in channels else []

    return light_scatter_channels + cd_channels + non_cd_channels + time_channel


def clean_marker_name(marker: str) -> str:
    if marker.startswith('CD'):
        if marker == 'CD45 RA' or marker == 'CD45 RO':
            return marker
        else:
            return re.match(r'(CD\d+\w*(\/CD\d+\w*)?) ?', marker).group(1)
    else:
        if 'lambda' in marker.lower():
            return 'Lambda'
        elif 'kappa' in marker.lower():
            return 'Kappa'
        elif marker.lower() == 'tdt':
            return 'TdT'
        elif marker.lower() == 'mpo':
            return 'MPO'
        else:
            return marker
