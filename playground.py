from unloop.detector import find_slow_patterns

sample = """
import pandas as pd

df = pd.DataFrame({"price": [10, 20], "qty": [1, 2]})

for i, row in df.iterrows():
    df.at[i, "total"] = row["price"] * row["qty"]
"""

for finding in find_slow_patterns(sample):
    print(f"Line {finding['line']}: {finding['message']}")

import ast
from unloop.rewriter import RowToColumn

expr = ast.parse('row["price"] * row["qty"]', mode="eval")
new_expr = RowToColumn("row", "df").visit(expr)
print(ast.unparse(new_expr))

from unloop.rewriter import is_simple_expression

good = ast.parse('row["price"] * row["qty"] + 5', mode="eval").body
bad = ast.parse('row["price"] * get_tax(row)', mode="eval").body
print(is_simple_expression(good, "row"))
print(is_simple_expression(bad, "row"))

from unloop.rewriter import match_iterrows_header

loop = ast.parse('for i, row in df.iterrows():\n    pass').body[0]
print(match_iterrows_header(loop))

other = ast.parse('for x in range(10):\n    pass').body[0]
print(match_iterrows_header(other))


from unloop.rewriter import rewrite_iterrows_loop

code = 'for i, row in df.iterrows():\n    df.at[i, "total"] = row["price"] * row["qty"]'
new = rewrite_iterrows_loop(ast.parse(code).body[0])
print(ast.unparse(new))

unsafe = 'for i, row in df.iterrows():\n    df.at[i, "total"] = get_tax(row)'
print(rewrite_iterrows_loop(ast.parse(unsafe).body[0]))


from unloop.rewriter import rewrite_code

new_code, changed = rewrite_code(sample)
print(new_code)
print("Rewritten loops at lines:", changed)


old_space = {}
exec(sample, old_space)

new_space = {}
exec(new_code, new_space)

print(old_space["df"])
print(new_space["df"])
print(old_space["df"].dtypes)
print(new_space["df"].dtypes)

from unloop.verifier import compare_dataframes

print(compare_dataframes(old_space["df"], new_space["df"]))
print(compare_dataframes(old_space["df"], old_space["df"]))


from unloop.verifier import describe_dtype_changes

print(describe_dtype_changes(old_space["df"], new_space["df"]))


import pandas as pd
from unloop.verifier import run_code

data = {"df": pd.DataFrame({"price": [10, 20], "qty": [1, 2]})}
loop_code = 'for i, row in df.iterrows():\n    df.at[i, "total"] = row["price"] * row["qty"]'

result = run_code(loop_code, data)
print(result["df"])
print(data["df"])