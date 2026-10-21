import numpy as np
import pandas as pd
from unloop import optimize

slow = """for i, row in df.iterrows():
    if row["price"] > 0.5:
        df.at[i, "label"] = "high"
    else:
        df.at[i, "label"] = "low"
"""

data = {"df": pd.DataFrame({"price": np.random.rand(10000)})}
result = optimize(slow, data)
print(result["status"], result.get("source", ""), result.get("attempts", ""), result.get("verdict", ""))
print(result["code"])