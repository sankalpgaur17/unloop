"""Check that rewritten code gives the same results as the original."""

import pandas as pd


def compare_dataframes(old, new):
    """Return 'identical', 'same_values', or 'different'."""
    try:
        pd.testing.assert_frame_equal(old, new)
        return "identical"
    except AssertionError:
        pass

    try:
        pd.testing.assert_frame_equal(old, new, check_dtype=False)
        return "same_values"
    except AssertionError:
        return "different"


def describe_dtype_changes(old, new):
    """List columns whose data type changed, like 'total: float64 -> int64'."""
    changes = []
    for column in old.columns:
        if column in new.columns and old[column].dtype != new[column].dtype:
            changes.append(f"{column}: {old[column].dtype} -> {new[column].dtype}")
    return changes