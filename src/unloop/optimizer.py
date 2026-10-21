"""The main entry point: rewrite, verify, and benchmark."""

from unloop.ai import ask_ai
from unloop.benchmark import time_code
from unloop.rewriter import rewrite_code
from unloop.verifier import verify_code


def check_candidate(code, new_code, variables, min_speedup):
    """Verify and benchmark one rewrite. Return a result dictionary."""
    try:
        verdict, notes = verify_code(code, new_code, variables)
    except Exception as error:
        return {"status": "rejected", "code": code, "notes": [f"verification failed: {error}"]}
    if verdict == "different":
        return {"status": "rejected", "code": code, "notes": notes}

    old_time = time_code(code, variables, repeats=3)
    new_time = time_code(new_code, variables, repeats=3)
    speedup = old_time / max(new_time, 1e-9)
    if speedup < min_speedup:
        return {"status": "not_faster", "code": code, "speedup": speedup}

    return {"status": "optimized", "code": new_code, "verdict": verdict, "notes": notes, "speedup": speedup}


def optimize(code, variables=None, min_speedup=1.5, use_ai=True, ai_attempts=3):
    """Try to speed up code safely. Return a result dictionary."""
    new_code, changed_lines = rewrite_code(code)
    if changed_lines:
        result = check_candidate(code, new_code, variables, min_speedup)
        result["source"] = "rules"
        return result

    if not use_ai:
        return {"status": "no_change", "code": code}

    result = {"status": "no_change", "code": code}
    feedback = None
    for attempt in range(ai_attempts):
        new_code = ask_ai(code, feedback=feedback)
        if not new_code or new_code.strip() == code.strip():
            break
        result = check_candidate(code, new_code, variables, min_speedup)
        result["source"] = "ai"
        result["attempts"] = attempt + 1
        if result["status"] == "optimized":
            return result
        problem = "; ".join(result.get("notes", [])) or result["status"]
        feedback = f"Your rewrite:\n{new_code}\nProblem: {problem}"
    return result