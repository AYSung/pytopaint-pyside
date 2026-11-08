# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

import json
import math
import re
from pathlib import Path

import anndata as ad
import numpy as np
import numpy.typing as npt
import pandas as pd
from pyreflow.typing import AnyCoreDataset

from pytopaint.channels import clean_marker_name, sort_channels
from pytopaint.colors import Color
from pytopaint.config import (
    get_default_scaling_factor,
    get_lower_asinh_bound,
    get_resolution,
    get_upper_asinh_bound,
    get_zoom_resolution,
)
from pytopaint.layout import dict_to_yaml, get_best_layout, to_grid


class FlowData:
    fcs: AnyCoreDataset
    adata: ad.AnnData

    def __init__(
        self,
        adata: ad.AnnData,
        fcs: AnyCoreDataset | None,
    ) -> None:
        self.fcs = fcs
        self.adata = adata

        self.set_scale(
            scaling_factor=adata.uns.get(
                'scaling_factor', get_default_scaling_factor(self.bit_mode)
            ),
            lower_asinh_bound=adata.uns.get(
                'lower_asinh_bound', get_lower_asinh_bound()
            ),
            upper_asinh_bound=adata.uns.get(
                'upper_asinh_bound', get_upper_asinh_bound()
            ),
        )
        self.set_size(bins=get_resolution())
        self.set_zoom(bins=get_zoom_resolution())
        self.load_analyses()

    @classmethod
    def from_fcs(cls, fcs: AnyCoreDataset):
        time_index, time_label, _ = fcs.temporal
        scatter_indices = [
            i
            for i, label in enumerate(fcs.all_shortnames)
            if label.startswith('FSC-') or label.startswith('SSC-')
        ]
        fluoro_indices = [i for i, label in enumerate(fcs.all_longnames) if label]

        file_prefix = Path(fcs.fil).stem
        case_id = extract_case_number(file_prefix)

        data = fcs.data.to_numpy()

        if fcs.version in ['FCS3.0']:
            tube_name_kw = 'TUBE NAME'
            if (spill := fcs.nonstandard_keywords.get('SPILL')) is not None:
                # apply compensation
                spillover_matrix, markers = get_spillover_matrix(spill)
                _indices = [
                    i for i, label in enumerate(fcs.all_shortnames) if label in markers
                ]
                data = apply_compensation(data, spillover_matrix, _indices)

        elif fcs.version in ['FCS3.1', 'FCS3.2']:
            tube_name_kw = 'TUBENAME'

            # apply compensation
            markers, spillover_matrix = fcs.spillover
            _indices = [
                i for i, label in enumerate(fcs.all_shortnames) if label in markers
            ]
            data = apply_compensation(data, spillover_matrix, _indices)

        cleaned_channel_names: np.array[str] = clean_channel_names(
            fcs, scatter_indices + [time_index]
        )
        empty_channel_mask: np.array[bool] = cleaned_channel_names != ''
        adata = ad.AnnData(X=data[:, empty_channel_mask])

        adata.uns['filename'] = fcs.fil
        adata.uns['tube'] = fcs.nonstandard_keywords.get(tube_name_kw)
        adata.uns['case_id'] = case_id

        bit_mode = extract_bit_mode(fcs, scatter_indices[0])
        adata.uns['bit_mode'] = bit_mode
        adata.uns['scaling_factor'] = get_default_scaling_factor(bit_mode)

        adata.var_names = cleaned_channel_names[empty_channel_mask]
        adata.var['channel_type'] = np.select(
            [
                adata.var_names.isin(cleaned_channel_names[scatter_indices]),
                adata.var_names.isin(cleaned_channel_names[fluoro_indices]),
            ],
            ['scatter', 'fluoro'],
            default='other',
        )
        adata.var['pnn_label'] = np.array(fcs.all_shortnames)[empty_channel_mask]
        adata.var['pns_label'] = np.array(fcs.all_longnames)[empty_channel_mask]

        adata.obs['color'] = Color.GREY
        adata.obs['visible'] = True  # TODO: remove and use -1, -2 for hidden/excluded

        return cls(adata, fcs)

    @classmethod
    def from_pytometry(cls, adata: ad.AnnData):
        raise NotImplementedError
        return cls(adata)

    @property
    def id(self) -> str:
        if self.adata.uns['tube']:
            return f'{self.case_id} {self.adata.uns["tube"]}'
        else:
            return self.case_id

    @property
    def case_id(self) -> str:
        return self.adata.uns.get('case_id', Path(self.filename).stem)

    @property
    def bit_mode(self) -> int:
        return self.adata.uns.get('bit_mode', 18)

    @property
    def filename(self) -> str:
        return self.adata.uns.get('filename')

    @property
    def event_count(self) -> str:
        return self.adata.n_obs

    @property
    def tube(self) -> str:
        return self.adata.uns.get('tube')

    @property
    def highlighted_colors(self) -> list[Color]:
        highlighted_colors = self.adata.uns.get('highlighted_colors')
        if highlighted_colors is not None:
            return list(map(Color, highlighted_colors))
        else:
            return []

    @property
    def channels(self) -> list[str]:
        return sort_channels(self.adata.var_names)

    @property
    def ip_channels(self) -> list[str]:
        return (
            self.adata.var_names[
                self.adata.var_names.isin(['FSC-A', 'SSC-A'])
            ].to_list()
            + self.fluoro_channels
        )

    @property
    def fluoro_channels(self) -> list[str]:
        return sort_channels(
            self.adata.var_names[self.adata.var['channel_type'] == 'fluoro']
        )

    @property
    def channel_fluor_map(self) -> dict[str, str]:
        return _channel_fluor_map(
            self.adata.var['pnn_label'].loc[self.adata.var['pns_label'] != '']
        )

    @property
    def scaling_factor(self) -> int:
        return self.adata.uns.get(
            'scaling_factor', get_default_scaling_factor(self.bit_mode)
        )

    @property
    def lower_asinh_bound(self) -> float:
        return self.adata.uns.get('lower_asinh_bound', get_lower_asinh_bound())

    @property
    def upper_asinh_bound(self) -> float:
        return self.adata.uns.get('upper_asinh_bound', get_upper_asinh_bound())

    @property
    def state_df(self) -> pd.DataFrame:
        return self.adata.obs.reset_index(drop=True).astype({'color': 'uint8'}).copy()

    @property
    def memory_states(self) -> dict[int, pd.DataFrame | None]:
        def _get_memory_state(index: int) -> pd.DataFrame | None:
            memory_state = self.adata.obsm.get(f'mem_{index}')
            return (
                memory_state.reset_index(drop=True)
                if memory_state is not None
                else None
            )

        N_MEMORY_SLOTS = 5
        return {i: _get_memory_state(i) for i in range(N_MEMORY_SLOTS)}

    @property
    def layout(self) -> dict[tuple[int, int], tuple[str, str]]:
        layout_grid = self.adata.uns.get('layout')
        if layout_grid is None:
            return get_best_layout(channels=self.channels).grid
        else:
            return to_grid(json.loads(layout_grid))

    def set_scale(
        self,
        scaling_factor: int,
        lower_asinh_bound: float,
        upper_asinh_bound: float,
    ) -> None:
        self.adata.uns['scaling_factor'] = scaling_factor
        self.adata.uns['lower_asinh_bound'] = lower_asinh_bound
        self.adata.uns['upper_asinh_bound'] = upper_asinh_bound

        self.adata.layers['xform'] = asinh_transform(
            self.adata, scaling_factor=self.adata.uns['scaling_factor']
        )
        self.adata.var['lower_bound'] = lower_clip_limits(self.adata, lower_asinh_bound)
        self.adata.var['upper_bound'] = upper_clip_limits(self.adata, upper_asinh_bound)

    def set_size(self, bins: int) -> None:
        self.adata.layers['bin'] = discretize_data(self.adata, bins)
        self.binned_df = pd.DataFrame(
            self.adata.layers['bin'], columns=self.adata.var_names
        )
        self.axis_ticks = get_axis_ticks(self.adata, bins)

    def set_zoom(self, bins: int) -> None:
        self.adata.layers['zoom'] = discretize_data(self.adata, bins)
        self.zoom_df = pd.DataFrame(
            self.adata.layers['zoom'], columns=self.adata.var_names
        )
        self.zoom_axis_ticks = get_axis_ticks(self.adata, bins)

    def update_session_state(
        self,
        state: pd.DataFrame,
        memory_states: dict[int, pd.DataFrame],
        layout: dict[tuple[int, int], tuple[str, str]],
        highlighted_colors: list[Color],
    ):
        def _copy_state(_state: pd.DataFrame) -> pd.DataFrame:
            new_state = _state.copy()
            new_state.index = new_state.index.astype(str)
            return new_state

        self.adata.obs = _copy_state(state)

        memory_state_keys = [key for key in self.adata.obsm if key.startswith('mem_')]
        for i, memory_state in memory_states.items():
            key = f'mem_{i}'
            if memory_state is not None:
                self.adata.obsm[key] = _copy_state(memory_state)
            elif key in memory_state_keys:
                self.adata.obsm.pop(key)

        if self.layout != layout:
            self.adata.uns['layout'] = json.dumps(dict_to_yaml(layout))

        self.adata.uns['highlighted_colors'] = (
            highlighted_colors if highlighted_colors else None
        )

    def load_analyses(self) -> None:
        if 'umap' in self.adata.obsm:
            self.load_umap()

        if 'pca' in self.adata.obsm:
            self.load_pca()

    def unload_analyses(self) -> None:
        analysis_keys = [key for key in self.adata.obsm if not key.startswith('mem_')]
        for key in analysis_keys:
            self.adata.obsm.pop(key)

    def _load_analysis(self, data: np.ndarray, columns: list[str]) -> None:
        arr, axis_ticks = get_analysis_dims(data, columns, get_resolution())
        zoom_arr, zoom_axis_ticks = get_analysis_dims(
            data, columns, get_zoom_resolution()
        )

        self.binned_df = self.binned_df.assign(**dict(zip(columns, arr.T)))
        self.axis_ticks = self.axis_ticks | axis_ticks
        self.zoom_df = self.zoom_df.assign(**dict(zip(columns, zoom_arr.T)))
        self.zoom_axis_ticks = self.zoom_axis_ticks | zoom_axis_ticks

    def load_umap(self) -> None:
        self._load_analysis(self.adata.obsm['umap'], ['UMAP 1', 'UMAP 2'])

    def load_pca(self) -> None:
        data = self.adata.obsm['pca']
        self._load_analysis(data, [f'PC {i + 1}' for i in range(data.shape[1])])


def extract_bit_mode(fcs: AnyCoreDataset, index: int) -> int:
    pnr = int(
        fcs.standard_keywords(req_or_opt='both', root_or_meas='both').get(
            f'$P{index + 1}R', '262144'
        )
    )
    return int(math.log2(pnr))


def clean_channel_names(
    fcs: AnyCoreDataset, non_fluoro_indices: list[int]
) -> np.ndarray[str]:
    return np.where(
        np.isin(np.arange(0, fcs.par), non_fluoro_indices),
        fcs.all_shortnames,
        list(map(clean_marker_name, fcs.all_longnames)),
    )


def asinh_transform(
    adata: ad.AnnData, scaling_factor: float
) -> npt.NDArray[np.float32]:
    data = adata.X.copy()
    indices = np.arange(0, adata.n_vars)[adata.var['channel_type'] == 'fluoro']
    xform_data = np.arcsinh(data[:, indices] / scaling_factor)
    data[:, indices] = xform_data
    return data.astype(np.float32)


def lower_clip_limits(adata: ad.AnnData, lower_bound: float) -> np.ndarray:
    return np.where(
        adata.var['channel_type'] != 'other',
        np.where(
            adata.var['channel_type'] == 'fluoro',
            np.minimum(
                lower_bound,
                np.quantile(adata.layers['xform'], q=0.05, axis=0) - 0.5,
            ),
            0,
        ),
        np.min(adata.X, axis=0),
    )


def upper_clip_limits(adata: ad.AnnData, upper_bound: float) -> np.ndarray:
    return np.where(
        adata.var['channel_type'] != 'other',
        np.where(
            adata.var['channel_type'] == 'fluoro',
            np.maximum(
                upper_bound,
                np.quantile(adata.layers['xform'], q=0.95, axis=0) + 0.5,
            ),
            np.maximum(
                2 ** adata.uns.get('bit_mode', 18),
                np.quantile(adata.layers['xform'], q=0.95, axis=0),
            ),
        ),
        np.max(adata.X, axis=0),
    )


def clip_xform_data(adata: ad.AnnData) -> np.ndarray:
    a_min = adata.var['lower_bound']
    a_max = adata.var['upper_bound']

    return np.clip(adata.layers['xform'], a_min=a_min, a_max=a_max)


def discretize_data(adata: ad.AnnData, bins: int) -> np.ndarray:
    arr = clip_xform_data(adata)
    lower_bounds = adata.var['lower_bound'].to_numpy()
    bin_widths = (
        (adata.var['upper_bound'] - adata.var['lower_bound']) / bins
    ).to_numpy()
    return ((arr - lower_bounds) // bin_widths).astype(np.uint16)


def discretize_array(
    lower_bound: float, upper_bound: float, bins: int, arr: npt.NDArray
) -> npt.NDArray:
    bin_width = (upper_bound - lower_bound) / bins
    return (arr - lower_bound) // bin_width


def get_axis_ticks(adata: ad.AnnData, bins: int) -> dict[str, list[tuple[int, str]]]:
    def _scatter_axis_ticks(channel: str) -> list[tuple[int, str]]:
        tick_positions = discretize_array(
            **bounds[channel], bins=bins, arr=SCATTER_TICK_VALUES
        )
        return list(zip(tick_positions, SCATTER_TICK_LABELS))

    def _fluoro_axis_ticks(channel: str) -> list[tuple[int, str]]:
        upper_bound = bounds[channel]['upper_bound']
        tick_values = np.fromiter(
            filter(lambda x: x < upper_bound, FLUORO_TICK_VALUES),
            dtype=float,
        )
        tick_positions = discretize_array(**bounds[channel], bins=bins, arr=tick_values)
        return list(zip(tick_positions, FLUORO_TICK_LABELS))

    def _other_axis_ticks(channel: str) -> list[tuple[int, str]]:
        tick_positions = discretize_array(
            **bounds[channel],
            bins=bins,
            arr=np.linspace(0, bounds[channel]['upper_bound'], 5),
        )
        return [(pos, None) for pos in tick_positions]

    bounds = adata.var[['lower_bound', 'upper_bound']].to_dict(orient='index')
    scaling_factor = adata.uns['scaling_factor']

    if adata.uns.get('bit_mode') == 22:
        SCATTER_TICK_VALUES = np.arange(0, 2**22, 500_000)
        SCATTER_TICK_LABELS = ['0', None, '1e6', None, '2e6', None, '3e6', None, '4e6']
    else:
        SCATTER_TICK_VALUES = np.arange(0, 2**18, 50_000)
        SCATTER_TICK_LABELS = ['0', None, '1e5', None, '2e5', None, '3e5']

    scatter_axis_ticks = {
        channel: _scatter_axis_ticks(channel)
        for channel in adata.var_names[adata.var['channel_type'] == 'scatter']
    }

    FLUORO_TICK_VALUES = [
        math.asinh(x / scaling_factor)
        for x in [-100, 0, 100, 1_000, 10_000, 100_000, 1_000_000]
    ]
    FLUORO_TICK_LABELS = [None, '0', None, '1e3', '1e4', '1e5', '1e6', '1e7']

    fluoro_axis_ticks = {
        channel: _fluoro_axis_ticks(channel)
        for channel in adata.var_names[adata.var['channel_type'] == 'fluoro']
    }

    other_axis_ticks = {
        channel: _other_axis_ticks(channel)
        for channel in adata.var_names[adata.var['channel_type'] == 'other']
    }

    return scatter_axis_ticks | fluoro_axis_ticks | other_axis_ticks


def _channel_fluor_map(pnn_labels: pd.Series):
    return {name: f'{name} ({pnn[:-2]})' for name, pnn in pnn_labels.items()}


def extract_case_number(filename: str) -> str:
    if match := re.match(r'[ZY][- ](\d{2})?[- ]?(\d{4,}).*$', filename):
        return f'IP{match.group(1) or "xx"}-{int(match.group(2)):05}'
    else:
        return filename


def get_analysis_dims(
    data: np.ndarray, columns: list[str], bins: int
) -> tuple[np.ndarray, dict[str, list[tuple[int, str]]]]:
    def _umap_axis_ticks(column: str) -> list[tuple[int, str]]:
        tick_positions = discretize_array(
            **bounds[column], bins=bins, arr=np.array([0])
        )
        return list(zip(tick_positions, ['0']))

    bounds = {
        column: {
            'lower_bound': np.amin(row) - (0.05 * np.ptp(row)),
            'upper_bound': np.amax(row) + (0.05 * np.ptp(row)),
        }
        for column, row in zip(columns, data.T)
    }
    bin_arr = np.array(
        [
            discretize_array(**bounds[column], bins=bins, arr=row)
            for column, row in zip(columns, data.T)
        ]
    ).T.astype(np.uint16)

    axis_ticks = {column: _umap_axis_ticks(column) for column in columns}
    return bin_arr, axis_ticks


def get_spillover_matrix(
    matrix_string: str,
) -> tuple[npt.NDArray[np.float32], list[str]]:
    """
    Code is modified from: https://github.com/whitews/FlowUtils
    Pedersen NW, Chandran PA, Qian Y, et al. Automated Analysis of Flow Cytometry
    Data to Reduce Inter-Lab Variation in the Detection of Major Histocompatibility
    Complex Multimer-Binding T Cells. Front Immunol. 2017;8:858.
    Published 2017 Jul 26. doi:10.3389/fimmu.2017.00858

    Compensate NumPy event data given spillover matrix. Extracts spillover matrix from FCS text entry.

    :param text: Text value from the $SPILL or $SPILLOVER metadata keyword in an FCS file
    :return: A tuple containing: (spillover matrix new_spill, column headers)
    """
    spill = matrix_string.split(',')
    n = int(spill[0])
    markers = spill[1 : (n + 1)]
    markers = [item.strip().replace('\n', '') for item in markers]
    items = [item.strip().replace('\n', '') for item in spill[n + 1 :]]
    new_spill = np.reshape(list(map(float, items)), (n, n))
    return new_spill, markers


def apply_compensation(
    data: npt.NDArray[np.float32],
    spill_matrix: npt.NPArray[np.float32],
    indices: list[int],
) -> npt.NDArray[np.float32]:
    """
    Code is modified from: https://github.com/whitews/FlowUtils
    Pedersen NW, Chandran PA, Qian Y, et al. Automated Analysis of Flow Cytometry
    Data to Reduce Inter-Lab Variation in the Detection of Major Histocompatibility
    Complex Multimer-Binding T Cells. Front Immunol. 2017;8:858.
    Published 2017 Jul 26. doi:10.3389/fimmu.2017.00858
    Compensate NumPy event data given spillover matrix.

    :param data: NumPy array of the event data
    :param spill_matrix: Compensation matrix as a NumPy array (without headers)
    :param fluoro_indices: List of fluorescent markers in the order found in the columns of the provided spill_matrix.
    :return: Polars dataframe of compensated event data with the
        non-fluorescent columns unmodified.
    """
    comp_data = np.linalg.solve(spill_matrix.T, data[:, indices].T).T
    data[:, indices] = comp_data

    return data.astype(np.float32)
