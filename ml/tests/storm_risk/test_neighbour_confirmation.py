import numpy as np
import pandas as pd
import xarray as xr

from ml.storm_risk.confirmation.neighbour import confirm_neighbours


def test_neighbour_confirmation():
    values = np.zeros((4, 1, 4))
    values[0, 0, :3] = .9
    values[1, 0, 1] = .9
    values[3, 0, 3] = .99
    grid = xr.DataArray(values, dims=('time', 'lat', 'lon'), coords=dict(time=pd.date_range('2020-01-01', periods=4, freq='h'), lat=[31.5], lon=[76, 76.1, 76.2, 79]))
    result = confirm_neighbours(grid, .7, .3, 2, 3)
    assert result[0, 0, :3].all() and result[1, 0, 1]
    assert not result[:, 0, 3].any()
    future = grid.copy()
    future.values[2:] = 1
    np.testing.assert_array_equal(result[:2], confirm_neighbours(future, .7, .3, 2, 3)[:2])
    # A gap does not make an old neighbouring exceedance one hour old.
    gap = grid.isel(time=[0, 3]).copy()
    gap.values[1, 0, 1] = .9
    assert not confirm_neighbours(gap, .7, .3, 2, 3)[1, 0, 1]
