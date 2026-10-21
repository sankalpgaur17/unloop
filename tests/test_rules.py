import numpy as np
import pandas as pd

from unloop import optimize
from unloop.rewriter import rewrite_code
from unloop.verifier import verify_code


def make_data():
    n = 2000
    return {
        "pd": pd,
        "lookup": {"x": 1, "y": 2},
        "df": pd.DataFrame({
            "price": np.random.rand(n),
            "qty": np.random.rand(n),
            "name": ["  apple  "] * n,
            "code": ["x", "y"] * (n // 2),
        }),
    }


def check_rule(code, expected):
    new_code, changed = rewrite_code(code)
    assert changed, "the rule should have matched"
    assert new_code == expected
    verdict, notes = verify_code(code, new_code, make_data())
    assert verdict == "identical", notes


def test_rule_1_iterrows_loop():
    check_rule(
        'for i, row in df.iterrows():\n    df.at[i, "total"] = row["price"] * row["qty"]',
        "df['total'] = df['price'] * df['qty']",
    )


def test_rule_2_apply_axis_1():
    check_rule(
        'df["total"] = df.apply(lambda r: r["price"] * r["qty"], axis=1)',
        "df['total'] = df['price'] * df['qty']",
    )


def test_rule_3_string_lambda():
    check_rule(
        'df["clean"] = df["name"].apply(lambda s: s.strip())',
        "df['clean'] = df['name'].str.strip()",
    )


def test_rule_4_dict_lookup():
    check_rule(
        'df["num"] = df["code"].apply(lambda c: lookup[c])',
        "df['num'] = df['code'].map(lookup)",
    )


def test_rule_5_concat_loop():
    check_rule(
        'out = pd.DataFrame()\nfor k in range(20):\n    out = pd.concat([out, df.head(5)], ignore_index=True)',
        "out = pd.DataFrame()\nout = pd.concat([out] + [df.head(5) for k in range(20)], ignore_index=True)",
    )


def test_unsafe_code_is_left_alone():
    code = 'for i, row in df.iterrows():\n    df.at[i, "total"] = get_tax(row)'
    new_code, changed = rewrite_code(code)
    assert changed == []
    assert new_code == code


def test_comments_are_kept():
    code = '# totals\nfor i, row in df.iterrows():\n    df.at[i, "total"] = row["price"] * row["qty"]\nx = 1  # keep me'
    new_code, changed = rewrite_code(code)
    assert new_code == "# totals\ndf['total'] = df['price'] * df['qty']\nx = 1  # keep me"


def test_verifier_catches_wrong_code():
    code = 'df["total"] = df["price"] * df["qty"]'
    wrong = 'df["total"] = df["price"] + df["qty"]'
    verdict, notes = verify_code(code, wrong, make_data())
    assert verdict == "different"


def test_optimize_end_to_end_without_ai():
    code = 'for i, row in df.iterrows():\n    df.at[i, "total"] = row["price"] * row["qty"]'
    result = optimize(code, make_data(), use_ai=False)
    assert result["status"] == "optimized"
    assert result["source"] == "rules"
    assert result["verdict"] == "identical"


def test_no_change_without_ai():
    result = optimize("x = 1", use_ai=False)
    assert result["status"] == "no_change"