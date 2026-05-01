import pandas as pd
import geopandas as gpd

from shapely.geometry import Polygon


def get_selection_index(
    point_array: list[list[float, float]], df: pd.DataFrame, x_label: str, y_label: str
) -> pd.Series:
    if len(point_array) < 4:
        return pd.Index([])

    poly = Polygon(point_array)
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[x_label], df[y_label]))
    selection_index = gdf[gdf.within(poly)].index
    return selection_index
