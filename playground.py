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