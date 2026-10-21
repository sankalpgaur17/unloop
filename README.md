# unloop

**Turn slow pandas loops into fast, verified vectorized code.**

`unloop` finds slow patterns in your pandas and NumPy code, like `iterrows()` loops and `apply(axis=1)`, and rewrites them into fast vectorized operations. Every rewrite is **run and compared against your original code** before it's offered, so `unloop` only ever makes your code faster, never different.

```python
%%unloop
for i, row in df.iterrows():
    df.at[i, "total"] = row["price"] * row["qty"]
```

```
unloop: 2016x faster via rules, results identical. Running:
df['total'] = df['price'] * df['qty']
```

## Why unloop?

Row-by-row loops are one of the most common reasons pandas code is slow. Rewriting them by hand is easy to get subtly wrong, especially with missing values and data types. `unloop` does the rewrite for you **and proves it's correct** on your actual data.

- **Verified, not guessed.** Both versions run on private copies of your data, plus extra test data with missing values mixed in. If the results differ in any way, the rewrite is rejected.
- **Only when it's actually faster.** Every rewrite is benchmarked, and `unloop` only changes your code if it's at least 1.5x faster.
- **Your data stays untouched.** Verification and timing run on copies, never on your real variables.
- **Keeps your formatting.** Only the slow lines change; your comments and blank lines stay exactly as you wrote them.
- **Private by design.** The optional AI runs on your own computer through Ollama. Nothing is sent to the cloud.

## Installation

```bash
pip install unloop
```

Requires Python 3.9+ and pandas 2.0+.

**Optional:** for faster text operations, also install PyArrow:

```bash
pip install pyarrow
```

## Quick start

### In Jupyter notebooks

Load the extension once per notebook:

```python
%load_ext unloop
```

Then put `%%unloop` at the top of any cell:

```python
%%unloop
df["total"] = df.apply(lambda r: r["price"] * r["qty"], axis=1)
```

What happens next depends on what `unloop` finds:

| Result | What unloop does |
|---|---|
| Faster, results identical | Runs the fast version and shows you the new code |
| Faster, but data types change | Runs your **original** code and shows the faster version as a suggestion |
| No safe speedup found | Runs your original code unchanged |

To skip the AI and use only the built-in rules:

```python
%%unloop --no-ai
```

### In Python code

```python
import unloop

result = unloop.optimize(code, {"df": df})

print(result["status"])   # "optimized", "no_change", "rejected", or "not_faster"
print(result["code"])     # the optimized code, or your original if not optimized
```

## What unloop can rewrite

| Slow pattern | Becomes |
|---|---|
| `for i, row in df.iterrows(): df.at[i, "c"] = row["a"] * row["b"]` | `df["c"] = df["a"] * df["b"]` |
| `df["c"] = df.apply(lambda r: r["a"] * r["b"], axis=1)` | `df["c"] = df["a"] * df["b"]` |
| `df["c"] = df["s"].apply(lambda x: x.strip())` | `df["c"] = df["s"].str.strip()` |
| `df["c"] = df["k"].apply(lambda x: lookup[x])` | `df["c"] = df["k"].map(lookup)` |
| `for x in items: out = pd.concat([out, piece])` | `out = pd.concat([out] + [piece for x in items])` |

Code that doesn't match these rules can be handled by the optional AI fallback.

## Optional: AI fallback with Ollama

For slow code that none of the built-in rules recognize, `unloop` can ask a small coding model running **locally** on your computer.

1. Install Ollama from [ollama.com](https://ollama.com).
2. Download the model:

   ```bash
   ollama pull qwen2.5-coder:3b
   ```

That's it. `unloop` uses it automatically when Ollama is running. AI suggestions go through **exactly the same verification and benchmarking** as the built-in rules, and if a suggestion fails, `unloop` tells the AI what went wrong and lets it try again (up to 3 times).

Verified AI rewrites are saved in `~/.unloop/cache.json` on your computer, so the same code never needs the AI twice. Saved rewrites are re-verified on your current data every time they're used.

## How it stays safe

For every rewrite, `unloop`:

1. Runs your original code and the new code on separate private copies of your data.
2. Compares every resulting DataFrame: values, columns, index, and data types.
3. Repeats the comparison on a small copy of your data with missing values (`NaN`) inserted, to catch bugs your current data might not reveal.
4. Benchmarks both versions and keeps the new code only if it's meaningfully faster.

If anything fails, your original code is used.

## Limitations

- `unloop` compares DataFrames. Changes to other kinds of variables (lists, dictionaries, files written to disk) are not checked.
- Verification **runs** both versions of your code. Avoid using `%%unloop` on cells with side effects like writing files, sending emails, or calling external APIs.
- AI-generated code is run on copies of your data during verification. It comes from a model on your own machine, but as with any generated code, review it before relying on it in important work.
- The verification is thorough but not a mathematical proof. It tests your data and common edge cases, not every possible input.

## License

MIT License. Copyright (c) 2026 Sankalp Gaur. See [LICENSE](LICENSE) for details.