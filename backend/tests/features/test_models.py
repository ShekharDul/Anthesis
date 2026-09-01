import numpy as np
import pytest

from anthesis.features import FeatureTable


def _table() -> FeatureTable:
    return FeatureTable(
        times=np.asarray([0.25, 0.75, 1.25, 1.75], dtype=np.float32),
        values=np.asarray([[1, 2], [3, 4], [5, 6], [7, 8]], dtype=np.float32),
        columns=("energy", "brightness"),
        units=("ratio", "Hz"),
    )


def test_feature_table_is_immutable_and_addressable_by_name() -> None:
    table = _table()

    assert table.column("brightness") == pytest.approx([2, 4, 6, 8])
    assert not table.values.flags.writeable
    with pytest.raises(KeyError):
        table.column("missing")


def test_feature_table_aggregates_supplied_section_intervals() -> None:
    sections = _table().aggregate_intervals([0, 1, 2])

    assert sections.times == pytest.approx([0.5, 1.5])
    np.testing.assert_allclose(sections.values, [[2, 3], [6, 7]])


def test_feature_table_rejects_shape_mismatch() -> None:
    with pytest.raises(ValueError, match="shape"):
        FeatureTable(
            times=np.asarray([0, 1], dtype=np.float32),
            values=np.ones((3, 1), dtype=np.float32),
            columns=("energy",),
            units=("ratio",),
        )
