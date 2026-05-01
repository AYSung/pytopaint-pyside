import pytest

import pandas as pd

from pytopaint.selection import get_selection_index


@pytest.fixture
def test_df_1():
    return pd.DataFrame(
        [(1, 1, 0), (1, 3, 0), (3, 3, 0), (3, 1, 0), (2, 2, 2)], columns=["x", "y", "z"]
    )


def test_geometry_selection(test_df_1):
    points_1 = [[0, 0], [2, 0], [2, 4], [0, 4]]
    points_2 = [[4, 0], [1, 0], [1, 4], [4, 4]]

    assert get_selection_index(points_1, test_df_1, "x", "y").shape[0] == 2
    assert get_selection_index(points_1, test_df_1, "x", "y").to_list() == [0, 1]
    assert get_selection_index(points_2, test_df_1, "x", "y").shape[0] == 3
    assert get_selection_index(points_2, test_df_1, "x", "y").to_list() == [2, 3, 4]
