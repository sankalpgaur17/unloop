"""Check that rewritten code gives the same results as the original."""

import numpy as np
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


def copy_variables(variables):
    """Copy DataFrames, Series, and arrays so the user's real data never changes."""
    copied = {}
    for name, value in variables.items():
        if isinstance(value, (pd.DataFrame, pd.Series, np.ndarray)):
            copied[name] = value.copy()
        else:
            copied[name] = value
    return copied


def run_code(code, variables):
    """Run code in a private workspace and return everything it created."""
    space = copy_variables(variables)
    exec(code, space)
    return space