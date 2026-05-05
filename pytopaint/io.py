import math
from pathlib import Path

import flowkit

# import polars as pl
import pandas as pd


LINEAR_PARAMETERS = ['FSC-A', 'FSC-H', 'SSC-A', 'SSC-H', 'Time']
LOWER_ASINH = -1
UPPER_ASINH = 8
UPPER_LINEAR = 255_000


def test_df() -> pd.DataFrame:
    return read_fcs('pytopaint/resources/normal_01_B.fcs')


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


def to_df(self, source: str, subsample: bool = None, indices: list[int] = list()):
    if subsample is None:
        subsample = self.subsample

    return self.sample.as_dataframe(
        source=source,
        col_names=self.channels,
    )


def _get_channels(df: pd.DataFrame) -> list[str]:
    # PHYSICAL_PARAMETERS = ['FSC-A', 'FSC-H', 'SSC-A', 'SSC-H', 'Time']
    # used_channels = df.loc[lambda x: x.pnn.isin(PHYSICAL_PARAMETERS) | (x.pns != ''), ['pnn', 'pns']]

    return df.pns.mask(lambda x: x == '').fillna(df.pnn).to_list()


def _get_compensation(metadata: dict[str, str]) -> str | None:
    return metadata.get('spill') or metadata.get('spillover')


def clip_df(df: pd.DataFrame) -> pd.DataFrame:
    def clip_series(s: pd.DataFrame) -> pd.Series:
        if s.name in LINEAR_PARAMETERS:
            return s.clip(lower=0, upper=UPPER_LINEAR)
        else:
            return s.clip(lower=LOWER_ASINH, upper=UPPER_ASINH)

    return df.apply(clip_series, axis='index')


def bin_df(df: pd.DataFrame, n_bins: int) -> pd.DataFrame:
    def bin_series(s: pd.Series) -> pd.Series:
        lower_limit = 0 if s.name in LINEAR_PARAMETERS else LOWER_ASINH
        upper_limit = UPPER_LINEAR if s.name in LINEAR_PARAMETERS else UPPER_ASINH
        bin_borders = [lower_limit] + [
            lower_limit + (((n + 1) / n_bins) * (upper_limit - lower_limit))
            for n in range(n_bins)
        ]

        return pd.cut(
            s, bins=bin_borders, include_lowest=True, labels=list(range(n_bins))
        ).astype(int)

    return df.apply(bin_series, axis='index')


def read_fcs(path: str | Path):
    if isinstance(path, str):
        path = Path(path)

    sample = flowkit.Sample(path, sample_id=path.stem)
    channels = _get_channels(sample.channels)
    return to_xform_df(sample, channels).pipe(clip_df)
