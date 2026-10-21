"""Find slow pandas patterns in Python code."""

import ast



def find_slow_patterns(code):
    """Return a list of slow patterns found in the given code."""
    tree = ast.parse(code)
    findings = []

    for node in ast.walk(tree):
        # Look for loops like: for i, row in df.iterrows():
        if isinstance(node, ast.For):
            call = node.iter
            if(
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "iterrows"
            ):
                findings.append({
                    "pattern": "iterrows_loop",
                    "line": node.lineno,
                    "message": "Row-by-row loop with iterrows() is slow.",
                })
    return findings