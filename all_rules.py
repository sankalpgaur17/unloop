import numpy as np
import pandas as pd
from unloop import optimize

n = 10000
data = {
    "pd": pd,
    "lookup": {"x": 1, "y": 2},
    "df": pd.DataFrame({
        "price": np.random.rand(n),
        "qty": np.random.rand(n),
        "name": ["  apple  "] * n,
        "code": ["x", "y"] * (n // 2),
    }),
}

tests = {
    "1. iterrows loop": 'for i, row in df.iterrows():\n    df.at[i, "total"] = row["price"] * row["qty"]',
    "2. apply axis=1": 'df["total"] = df.apply(lambda r: r["price"] * r["qty"], axis=1)',
    "3. string lambda": 'df["clean"] = df["name"].apply(lambda s: s.strip())',
    "4. dict lookup": 'df["num"] = df["code"].apply(lambda c: lookup[c])',
    "5. concat loop": 'out = pd.DataFrame()\nfor k in range(200):\n    out = pd.concat([out, df.head(5)], ignore_index=True)',
}

for name, code in tests.items():
    result = optimize(code, data)
    speed = f"{result['speedup']:.0f}x" if "speedup" in result else ""
    print(f"{name}: {result['status']} {result.get('verdict', '')} {speed}")