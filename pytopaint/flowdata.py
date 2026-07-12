# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

import math
import re
from pathlib import Path

import anndata as ad
import flowio
import flowutils
import numpy as np
from sklearn.preprocessing import RobustScaler
from umap import UMAP

from pytopaint.colors import Color
from pytopaint.config import (
    get_lower_asinh_bound,
    get_resolution,
    get_scaling_factor,
    get_upper_asinh_bound,
)

PHYSICAL_PARAMETERS = ['FSC-A', 'FSC-H', 'SSC-A', 'SSC-H']
UPPER_PHYSICAL = 255_000


def read_fcs(fcs: flowio.FlowData) -> ad.AnnData:
    cleaned_channel_names = clean_channel_names(fcs)
    empty_channel_mask = cleaned_channel_names != ''
    adata = ad.AnnData(X=compensate(fcs)[:, empty_channel_mask].astype(np.float32))

    adata.uns['filename'] = fcs.name
    adata.uns['tube'] = fcs.text.get('tube name')
    adata.uns['id'] = (
        f'{extract_case_number(Path(fcs.name).stem)} {adata.uns["tube"]}'
        if adata.uns['tube']
        else f'{extract_case_number(Path(fcs.name).stem)}'
    )

    adata.var_names = cleaned_channel_names[empty_channel_mask]
    adata.var['channel_type'] = np.select(
        [
            adata.var_names.isin(cleaned_channel_names[fcs.scatter_indices]),
            adata.var_names == cleaned_channel_names[fcs.time_index],
        ],
        ['scatter', 'time'],
        default='fluoro',
    )
    adata.var['pnn_label'] = np.array(fcs.pnn_labels)[empty_channel_mask]
    adata.var['pns_label'] = np.array(fcs.pns_labels)[empty_channel_mask]

    adata.obs['color'] = Color.GREY
    adata.obs['visible'] = True

    return initialize(adata)


def initialize(
    adata: ad.AnnData,
) -> ad.AnnData:
    set_scale(
        adata,
        scaling_factor=adata.uns.get('scaling_factor', get_scaling_factor()),
        lower_asinh_bound=adata.uns.get('lower_asinh_bound', get_lower_asinh_bound()),
        upper_asinh_bound=adata.uns.get('upper_asinh_bound', get_upper_asinh_bound()),
    )
    set_size(adata, bins=adata.uns.get('bins', get_resolution()))
    return adata


def set_scale(
    adata: ad.AnnData,
    scaling_factor: int,
    lower_asinh_bound: float,
    upper_asinh_bound: float,
) -> None:
    adata.uns['scaling_factor'] = scaling_factor
    adata.uns['lower_asinh_bound'] = lower_asinh_bound
    adata.uns['upper_asinh_bound'] = upper_asinh_bound

    adata.layers['xform'] = asinh_transform(
        adata, scaling_factor=adata.uns['scaling_factor']
    )
    adata.var['lower_bound'] = lower_clip_limits(adata)
    adata.var['upper_bound'] = upper_clip_limits(adata)


def set_size(adata: ad.AnnData, bins: int) -> None:
    adata.uns['bins'] = bins
    adata.layers['bin'] = discretize_data(adata)


def clean_channel_names(fcs: flowio.FlowData) -> np.ndarray[str]:
    return np.where(
        np.isin(
            np.arange(0, fcs.channel_count), fcs.scatter_indices + [fcs.time_index]
        ),
        fcs.pnn_labels,
        list(map(_clean_marker_name, fcs.pns_labels)),
    )


def compensate(fcs: flowio.FlowData) -> np.ndarray:
    if spill := fcs.text.get('spill') or fcs.text.get('spillover'):
        spill_matrix, _ = flowutils.compensate.get_spill(spill)
        return flowutils.compensate.compensate(
            fcs.as_array(), spill_matrix, fcs.fluoro_indices
        )

    return fcs.as_array().astype(np.float32)


def asinh_transform(adata: ad.AnnData, scaling_factor: float) -> np.ndarray:
    return flowutils.transforms.asinh(
        adata.X,
        channel_indices=np.arange(0, adata.n_vars)[
            adata.var['channel_type'] == 'fluoro'
        ],
        t=scaling_factor / math.sinh(1),
        m=1 / math.log(10),
        a=0,
    ).astype(np.float32)


# TODO: adjust floor with config
def lower_clip_limits(adata: ad.AnnData) -> np.ndarray:
    return np.where(
        adata.var['channel_type'] == 'fluoro',
        np.minimum(
            get_lower_asinh_bound(),
            np.quantile(adata.layers['xform'], q=0.05, axis=0) - 0.5,
        ),
        0,
    )


# TODO: adjust ceiling with config
def upper_clip_limits(adata: ad.AnnData) -> np.ndarray:
    return np.where(
        adata.var['channel_type'] != 'time',
        np.where(
            adata.var['channel_type'] == 'fluoro',
            np.maximum(
                get_upper_asinh_bound(),
                np.quantile(adata.layers['xform'], q=0.95, axis=0) + 0.5,
            ),
            np.maximum(255_000.0, np.quantile(adata.layers['xform'], q=0.95, axis=0)),
        ),
        np.max(adata.X, axis=0),
    )


def clip_xform_data(adata: ad.AnnData) -> np.ndarray:
    a_min = adata.var['lower_bound']
    a_max = adata.var['upper_bound']

    return np.clip(adata.layers['xform'], a_min=a_min, a_max=a_max)


def discretize_data(adata: ad.AnnData) -> np.ndarray:
    arr = clip_xform_data(adata)
    bounds = adata.var[['lower_bound', 'upper_bound']].to_dict(orient='records')
    return np.array([
        discretize_array(**bounds[i], bins=adata.uns['bins'], arr=row)
        for i, row in enumerate(arr.T)
    ]).T.astype(np.uint16)


def discretize_array(
    lower_bound: float, upper_bound: float, bins: int, arr: np.ndarray
) -> np.ndarray:
    bins = np.linspace(lower_bound, upper_bound, num=bins)
    return np.searchsorted(bins, arr, side='left')


def get_umap_dims(
    adata: ad.AnnData,
) -> tuple[np.ndarray, dict[str, list[tuple[int, str]]]]:
    bounds = {
        channel: dict(
            lower_bound=np.amin(row) - (0.05 * np.ptp(row)),
            upper_bound=np.amax(row) + (0.05 * np.ptp(row)),
        )
        for channel, row in zip(['UMAP1', 'UMAP2'], adata.obsm['umap'].T)
    }
    adata.obsm['umap_bins'] = np.array([
        discretize_array(
            **bounds[channel],
            bins=adata.uns['bins'],
            arr=row,
        )
        for channel, row in zip(['UMAP1', 'UMAP2'], adata.obsm['umap'].T)
    ]).T.astype(np.uint16)

    umap_axis_ticks = _umap_axis_ticks(
        bins=adata.uns['bins'],
        channels=['UMAP1', 'UMAP2'],
        bounds=bounds,
    )
    return adata.obsm['umap_bins'], umap_axis_ticks


def umap_transform(arr: np.ndarray) -> np.ndarray:
    scaled_arr = RobustScaler().fit_transform(arr)
    umap = UMAP(init='pca', verbose=True, min_dist=0.4, n_neighbors=15, random_state=42)
    rng = np.random.default_rng(seed=42)
    umap.fit(rng.choice(scaled_arr, size=min(20_000, arr.shape[0]), replace=False))
    return umap.transform(scaled_arr)


def get_axis_ticks(
    adata: ad.AnnData,
) -> dict[str, list[tuple[int, str]]]:
    bounds = adata.var[['lower_bound', 'upper_bound']].to_dict(orient='index')
    bins = adata.uns['bins']
    scaling_factor = adata.uns['scaling_factor']

    scatter_axis_ticks = {
        channel_name: list(
            zip(
                discretize_array(
                    **bounds[channel_name],
                    bins=bins,
                    arr=np.arange(
                        0,
                        50_000 * (bounds[channel_name]['upper_bound'] // 50_000),
                        50_000,
                    ),
                ),
                ['0', None, '1e5', None, '2e5', None, '3e5'],
            )
        )
        for channel_name in adata.var_names[adata.var['channel_type'] == 'scatter']
    }
    fluoro_axis_ticks = _fluoro_axis_ticks(
        bins=bins,
        scaling_factor=scaling_factor,
        channels=adata.var_names[adata.var['channel_type'] == 'fluoro'],
        bounds=bounds,
    )

    time_axis_ticks = {
        'Time': list(
            zip(
                discretize_array(
                    **bounds['Time'],
                    bins=bins,
                    arr=np.linspace(0, bounds['Time']['upper_bound'], 5),
                ),
                [None, None, None, None, None],
            )
        )
    }
    return scatter_axis_ticks | fluoro_axis_ticks | time_axis_ticks


def _scatter_axis_ticks(
    bins: int,
    scaling_factor: float,
    channels: list[str],
    bounds: dict[int, dict[str, float]],
) -> dict[str, list[tuple[int, str]]]:

    return


def _fluoro_axis_ticks(
    bins: int,
    scaling_factor: float,
    channels: list[str],
    bounds: dict[int, dict[str, float]],
) -> dict[str, list[tuple[int, str]]]:
    return {
        channel_name: list(
            zip(
                discretize_array(
                    **bounds[channel_name],
                    bins=bins,
                    arr=np.array(
                        list(
                            filter(
                                lambda x: x < bounds[channel_name]['upper_bound'],
                                map(
                                    lambda x: math.asinh(x / scaling_factor),
                                    [-100, 0, 100, 1_000, 10_000, 100_000, 1_000_000],
                                ),
                            )
                        )
                    ),
                ),
                [None, '0', None, '1e3', '1e4', '1e5', '1e6', '1e7'],
            )
        )
        for channel_name in channels
    }


def _time_axis_ticks() -> dict[str, list[tuple[int, str]]]:
    return


def _umap_axis_ticks(
    bins: int,
    channels: list[str],
    bounds: dict[int, dict[str, float]],
) -> dict[str, list[tuple[int, str]]]:
    return {
        channel_name: list(
            zip(
                discretize_array(
                    **bounds[channel_name],
                    bins=bins,
                    arr=np.array([0]),
                ),
                ['0'],
            )
        )
        for channel_name in channels
    }


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


def extract_case_number(filename: str) -> str:
    if match := re.match(r'[ZY][- ](\d{2})?[- ]?(\d{4,}) [\w\- ]+$', filename):
        return f'IP{match.group(1) or "xx"}-{int(match.group(2)):05}'
    else:
        return filename
