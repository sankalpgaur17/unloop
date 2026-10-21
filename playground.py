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