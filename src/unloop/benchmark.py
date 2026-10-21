"""Measure how fast code runs."""

import time

from unloop.verifier import copy_variables


def time_code(code, variables=None, repeats=5):
    """Run code several times and return the fastest time in seconds."""
    if variables is None:
        variables = {}
    compiled = compile(code, "<unloop>", "exec")
    best = float("inf")
    for _ in range(repeats):
        space = copy_variables(variables)
        start = time.perf_counter()
        exec(compiled, space)
        elapsed = time.perf_counter() - start
        best = min(best, elapsed)
    return best