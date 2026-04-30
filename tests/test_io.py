import pytest

import flowkit
import pandas as pd


from pytopaint.io import bin_df, clip_df


@pytest.fixture
def test_df_1():
    return pd.DataFrame({"FSC-A": [-1, 100], "SSC-A": [-1, 100], "CD45": [4, 10]})


def test_clip(test_df_1):
    pd.testing.assert_frame_equal(
        clip_df(test_df_1),
        pd.DataFrame({"FSC-A": [0, 100], "SSC-A": [0, 100], "CD45": [4, 8]}),
    )


def test_bin(test_df_1):
    binned_df = bin_df(clip_df(test_df_1), n_bins=256)
    pd.testing.assert_frame_equal(
        binned_df,
        pd.DataFrame({"FSC-A": [0, 0], "SSC-A": [0, 0], "CD45": [142, 255]}),
    )
