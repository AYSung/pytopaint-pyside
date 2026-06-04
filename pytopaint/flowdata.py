import math
import re
from functools import partial

import flowkit
import pandas as pd

from pytopaint.config import appconfig

PHYSICAL_PARAMETERS = ['FSC-A', 'FSC-H', 'SSC-A', 'SSC-H']
UPPER_PHYSICAL = 255_000


class FlowData:
    def __init__(self, sample: flowkit.Sample):
        self.sample = sample
        self.channels = _get_channels(self.sample.channels)

        self.update_scale()

    @classmethod
    def from_path(cls, filepath: str):
        sample = flowkit.Sample(filepath)
        return cls(sample)

    @property
    def sorted_channels(self) -> list[str]:
        return sort_channels(self.channels)

    @property
    def axis_ticks(self) -> dict[str, list[tuple[int, str]]]:
        return {
            channel: get_axis_ticks(
                channel,
                n_bins=appconfig.resolution,
                scaling_factor=appconfig.scaling_factor,
                clip_limits=self.clip_limits,
            )
            for channel in self.channels
        }

    @property
    def binned_df(self) -> pd.DataFrame:
        return bin_df(
            self.xform_df, n_bins=appconfig.resolution, clip_limits=self.clip_limits
        ).astype('uint8')

    def update_scale(self) -> None:
        self.xform_df = to_xform_df(
            self.sample, channels=self.channels, scaling_factor=appconfig.scaling_factor
        )

        self.clip_limits = {
            channel: (
                lower_clip_limit(self.xform_df[channel]),
                upper_clip_limit(self.xform_df[channel]),
            )
            for channel in self.channels
        }


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
    if channel in PHYSICAL_PARAMETERS:
        ticks = [0, 50_000, 100_000, 150_000, 200_000, 250_000]
        scaled_ticks = bin_series(
            pd.Series(ticks, name=channel), n_bins=n_bins, clip_limits=clip_limits
        )
        return list(zip(scaled_ticks, ['0', None, '1e5', None, '2e5', None, '3e5']))
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
    channels: list[str],
    scaling_factor: float = 150,
):
    compensation = _get_compensation(sample.metadata)
    if compensation is not None:
        sample.apply_compensation(compensation)

    sample.apply_transform(_arcsinh_transformer(scaling_factor))

    return sample.as_dataframe(source='xform', col_names=channels)


def _arcsinh_transformer(factor) -> flowkit.transforms.AsinhTransform:
    return flowkit.transforms.AsinhTransform(
        param_t=factor * math.sinh(1), param_m=1 / math.log(10), param_a=0
    )


def sort_channels(channels: list[str] | set[str]) -> list[str]:
    LIGHT_SCATTER_CHANNELS = ['FSC-A', 'FSC-H', 'SSC-A', 'SSC-H']
    light_scatter_channels = sorted([
        channel for channel in channels if channel in LIGHT_SCATTER_CHANNELS
    ])
    cd_channels = sorted(
        [channel for channel in channels if channel.startswith('CD')],
        key=lambda s: int(re.match(r'CD(\d+) ?', s).group(1)),
    )
    non_cd_channels = sorted([
        channel
        for channel in channels
        if not channel.startswith('CD')
        and channel not in LIGHT_SCATTER_CHANNELS + ['Time']
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


def _get_compensation(metadata: dict[str, str]) -> str | None:
    return metadata.get('spill') or metadata.get('spillover')


def lower_clip_limit(s: pd.Series):
    if s.name in PHYSICAL_PARAMETERS + ['Time']:
        return 0
    else:
        return min(appconfig.lower_arcsinh_limit, s.quantile(0.05) - 0.5)


def upper_clip_limit(s: pd.Series):
    if s.name == 'Time':
        return s.max()
    if s.name in PHYSICAL_PARAMETERS:
        return UPPER_PHYSICAL
    else:
        return max(appconfig.upper_arcsinh_limit, s.quantile(0.95) + 0.5)


def bin_series(s: pd.Series, n_bins: int, clip_limits: dict[str, tuple[float, float]]):
    lower_limit, upper_limit = clip_limits[s.name]

    bin_borders = (
        [lower_limit]
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
