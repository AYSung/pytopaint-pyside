# Copyright (C) 2026 Andrew Y. Sung
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

import geopandas as gpd
import anndata as ad
import pandas as pd
from shapely.geometry import Polygon


def get_selection_index(
    point_array: list[list[float, float]], df: pd.DataFrame, x_label: str, y_label: str
) -> pd.Index:
    if len(point_array) < 4:
        return pd.Index([])

    poly = Polygon(point_array)
    gdf = gpd.GeoDataFrame(geometry=gpd.points_from_xy(df[x_label], df[y_label]))
    selection_index = gdf[gdf.within(poly)].index
    return selection_index
