from unloop.ai import ask_ai

slow = """for i, row in df.iterrows():
    if row["price"] > 0.5:
        df.at[i, "label"] = "high"
    else:
        df.at[i, "label"] = "low"
"""

print(ask_ai(slow))