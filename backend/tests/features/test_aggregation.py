import numpy as np
import pytest

from anthesis.features.aggregation import aggregate_columns


def test_aggregate_columns_supports_documented_reducers() -> None:
    values = np.asarray([[1, 2, 3, 4], [4, 3, 2, 1]], dtype=np.float32)

    np.testing.assert_allclose(
        aggregate_columns(values, 2, reducer="mean"), [[1.5, 3.5], [3.5, 1.5]]
    )
    np.testing.assert_allclose(
        aggregate_columns(values, 2, reducer="median"), [[1.5, 3.5], [3.5, 1.5]]
    )
    np.testing.assert_allclose(aggregate_columns(values, 2, reducer="max"), [[2, 4], [4, 2]])


def test_aggregate_columns_rejects_unknown_reducer() -> None:
    with pytest.raises(ValueError, match="Unknown reducer"):
        aggregate_columns(np.ones((2, 3), dtype=np.float32), 2, reducer="sum")
