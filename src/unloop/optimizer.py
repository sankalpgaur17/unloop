"""The main entry point: rewrite, verify, and benchmark."""

from unloop.benchmark import time_code
from unloop.rewriter import rewrite_code
from unloop.verifier import verify_code


def optimize(code, variables=None, min_speedup=1.5):
    """Try to speed up code safely. Return a result dictionary."""
    new_code, changed_lines = rewrite_code(code)
    if not changed_lines:
        return {"status": "no_change", "code": code}

    verdict, notes = verify_code(code, new_code, variables)
    if verdict == "different":
        return {"status": "rejected", "code": code, "notes": notes}

    old_time = time_code(code, variables, repeats=3)
    new_time = time_code(new_code, variables, repeats=3)
    speedup = old_time / max(new_time, 1e-9)
    if speedup < min_speedup:
        return {"status": "not_faster", "code": code, "speedup": speedup}

    return {
        "status": "optimized",
        "code": new_code,
        "verdict": verdict,
        "notes": notes,
        "lines": changed_lines,
        "speedup": speedup,
    }