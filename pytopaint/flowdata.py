# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

import math
import re
from functools import partial
from pathlib import Path

import flowkit
import pandas as pd
from sklearn.preprocessing import RobustScaler
from umap import UMAP

from pytopaint.config import appconfig

PHYSICAL_PARAMETERS = ['FSC-A', 'FSC-H', 'SSC-A', 'SSC-H']
ADDED_PARAMETERS = ['UMAP1', 'UMAP2']
NON_IP_PARAMETERS = PHYSICAL_PARAMETERS + ['Time'] + ADDED_PARAMETERS
UPPER_PHYSICAL = 255_000


class FlowData:
    def __init__(self, sample: flowkit.Sample, id: str, tube: str):
        self.sample = sample
        self.tube = tube
        self.id = id

        self.reset()

    @classmethod
    def from_path(cls, filepath: Path):
        sample = flowkit.Sample(filepath)
        tube = sample.metadata.get('tube name', None)
        id = (
            extract_case_number(sample.metadata['src'])
            if 'src' in sample.metadata
            else filepath.stem
        )

        sample.metadata = sample._get_metadata_for_export(source='raw') | {
            k: v for k, v in sample.metadata.items() if k in ['spill', 'spillover']
        }
        return cls(sample, id, tube)

    @property
    def sorted_channels(self) -> list[str]:
        return sort_channels(self.xform_df.columns)

    @property
    def channel_details(self) -> list[str]:
        return [
            f'{marker} ({fluor})' if marker else fluor
            for fluor, marker in self.sample.channels[['pnn', 'pns']].to_records(
                index=False
            )
            if fluor not in _get_empty_channels(self.sample.channels)
        ]

    @property
    def name(self) -> str:
        if self.tube is not None:
            return f'{self.id} {self.tube}'
        else:
            return f'{self.id}'

    def update_scale(self) -> None:
        self.xform_df = to_xform_df(
            self.sample, scaling_factor=appconfig.scaling_factor
        )
        self.clip_limits = get_clip_limits(self.xform_df)

    def update_bins(self) -> None:
        self.binned_df = bin_df(
            self.xform_df, n_bins=appconfig.resolution, clip_limits=self.clip_limits
        ).astype('uint8')

        self.axis_ticks = {
            channel: get_axis_ticks(
                channel,
                n_bins=appconfig.resolution,
                scaling_factor=appconfig.scaling_factor,
                clip_limits=self.clip_limits,
            )
            for channel in self.xform_df.columns
        }

    def add_umap_dims(self) -> None:
        umap_df = umap_transform(self.xform_df)
        self.xform_df = self.xform_df.assign(
            UMAP1=umap_df['UMAP1'], UMAP2=umap_df['UMAP2']
        )
        self.clip_limits = self.clip_limits | get_clip_limits(umap_df)

        self.update_bins()

    def reset(self) -> None:
        self.update_scale()
        self.update_bins()


def bin_df(
    df: pd.DataFrame, n_bins: int, clip_limits=dict[str, tuple[float, float]]
) -> pd.DataFrame:
    return df.apply(partial(clip_series, clip_limits=clip_limits)).apply(
        partial(bin_series, n_bins=n_bins, clip_limits=clip_limits)
    )


def get_axis_ticks(
    channel: str,
    n_bins: int,
    scaling_factor: float,
    clip_limits: dict[str, tuple[float, float]],
) -> list[tuple[int, str]]:
    lower_limit, upper_limit = clip_limits[channel]

    if channel == 'Time':
        quarter = n_bins / 4
        ticks = [(i * quarter) for i in range(5)]
        return [(tick, None) for tick in ticks]
    elif channel in PHYSICAL_PARAMETERS:
        ticks = [0, 50_000, 100_000, 150_000, 200_000, 250_000]
        scaled_ticks = bin_series(
            pd.Series(ticks, name=channel), n_bins=n_bins, clip_limits=clip_limits
        )
        return list(zip(scaled_ticks, ['0', None, '1e5', None, '2e5', None, '3e5']))
    elif channel in ADDED_PARAMETERS:
        ticks = [0]
        scaled_ticks = bin_series(
            pd.Series(ticks, name=channel), n_bins=n_bins, clip_limits=clip_limits
        )
        return list(zip(scaled_ticks, ['0']))
    else:
        ticks = list(
            filter(
                lambda x: (x >= lower_limit) and (x <= upper_limit),
                map(
                    lambda x: math.asinh(x / scaling_factor),
                    [-100, 0, 100, 1_000, 10_000, 100_000, 1_000_000, 10_000_000],
                ),
            )
        )
        scaled_ticks = bin_series(
            pd.Series(ticks, name=channel), n_bins=n_bins, clip_limits=clip_limits
        )
        return list(
            zip(scaled_ticks, [None, '0', None, '1e3', '1e4', '1e5', '1e6', '1e7'])
        )


def to_xform_df(
    sample: flowkit.Sample,
    scaling_factor: float,
):
    compensation = _get_compensation(sample.metadata)
    if compensation is not None:
        sample.apply_compensation(compensation)

    sample.apply_transform(_arcsinh_transformer(scaling_factor))
    df = sample.as_dataframe(source='xform', col_names=_get_channels(sample.channels))
    if empty_channels := _get_empty_channels(sample.channels):
        df = df.drop(columns=empty_channels)
    return df


def _arcsinh_transformer(factor) -> flowkit.transforms.AsinhTransform:
    return flowkit.transforms.AsinhTransform(
        param_t=factor * math.sinh(1), param_m=1 / math.log(10), param_a=0
    )


def sort_channels(channels: list[str] | set[str]) -> list[str]:
    light_scatter_channels = sorted(
        list(filter(lambda x: x in PHYSICAL_PARAMETERS, channels))
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


def _clean_marker_name(marker: str) -> str:
    if marker.startswith('CD'):
        if marker == 'CD45 RA' or marker == 'CD45 RO':
            return marker
        elif re.match(r'CD\d+$', marker):
            return marker
        else:
            return re.match(r'(CD\d+\w*) ?', marker).group(1)
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


def _get_channels(df: pd.DataFrame) -> list[str]:
    return [
        f'{_clean_marker_name(marker)}' if marker else fluor
        for fluor, marker in df[['pnn', 'pns']].to_records(index=False)
    ]


def _get_empty_channels(df: pd.DataFrame) -> list[str]:
    return [
        fluor
        for fluor, marker in df[['pnn', 'pns']].to_records(index=False)
        if not marker and fluor not in PHYSICAL_PARAMETERS + ['Time']
    ]


def _get_compensation(metadata: dict[str, str]) -> str | None:
    return metadata.get('spill') or metadata.get('spillover')


def get_clip_limits(df: pd.DataFrame):
    return {
        channel: (
            lower_clip_limit(df[channel]),
            upper_clip_limit(df[channel]),
        )
        for channel in df.columns
    }


def lower_clip_limit(s: pd.Series):
    if s.name in PHYSICAL_PARAMETERS + ['Time']:
        return 0
    elif s.name in ADDED_PARAMETERS:
        return 1.05 * s.min()
    else:
        return min(appconfig.lower_arcsinh_limit, s.quantile(0.05) - 0.5)


def upper_clip_limit(s: pd.Series):
    if s.name == 'Time':
        return s.max()
    elif s.name in PHYSICAL_PARAMETERS:
        return UPPER_PHYSICAL
    elif s.name in ADDED_PARAMETERS:
        return 1.05 * s.max()
    else:
        return max(appconfig.upper_arcsinh_limit, s.quantile(0.95) + 0.5)


def bin_series(s: pd.Series, n_bins: int, clip_limits: dict[str, tuple[float, float]]):
    lower_limit, upper_limit = clip_limits[s.name]

    bin_borders = (
        [float('-inf')]
        + [
            lower_limit + (((n + 1) / n_bins) * (upper_limit - lower_limit))
            for n in range(n_bins - 1)
        ]
        + [float('inf')]
    )

    return pd.cut(
        s, bins=bin_borders, include_lowest=True, labels=list(range(n_bins))
    ).astype(int)


def clip_series(s: pd.Series, clip_limits: dict[str, tuple[float, float]]):
    lower_limit, upper_limit = clip_limits[s.name]

    return s.clip(lower=lower_limit, upper=upper_limit)


def extract_case_number(filename: str) -> str:
    if match := re.match(r'\w[- ](\d{2})[- ](\d{4,}) [\w\- ]+$', filename):
        return f'IP{match.group(1)}-{int(match.group(2)):05}'
    elif match := re.match(r'\w[- ](\d{4,}) [\w\- ]+', filename):
        return f'IPxx-{int(match.group(1)):05}'
    else:
        return filename


def umap_transform(df: pd.DataFrame) -> pd.DataFrame:
    non_linear_df = df[
        [column for column in df.columns if column not in NON_IP_PARAMETERS]
    ]
    scaled_df = RobustScaler().fit_transform(non_linear_df)
    umap = UMAP(init='pca', min_dist=0.4, n_neighbors=15)
    umap.fit(pd.DataFrame(scaled_df).sample(min(20_000, df.shape[0])))

    return pd.DataFrame(umap.transform(scaled_df), columns=['UMAP1', 'UMAP2'])
