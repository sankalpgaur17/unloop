"""Rewrite slow pandas patterns into fast vectorized code."""

import ast


class RowToColumn(ast.NodeTransformer):
    """Turn row["col"] into df["col"]."""

    def __init__(self, row_name, df_name):
        self.row_name = row_name
        self.df_name = df_name

    def visit_Subscript(self, node):
        self.generic_visit(node)
        if isinstance(node.value, ast.Name) and node.value.id == self.row_name:
            node.value = ast.Name(id=self.df_name, ctx=ast.Load())
        return node


SAFE_OPERATORS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)


def is_simple_expression(node, row_name):
    """Check that an expression only uses row["col"], numbers, and math."""
    if isinstance(node, ast.Constant):
        return isinstance(node.value, (int, float))
    if isinstance(node, ast.Subscript):
        return (
            isinstance(node.value, ast.Name)
            and node.value.id == row_name
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        )
    if isinstance(node, ast.BinOp):
        return (
            isinstance(node.op, SAFE_OPERATORS)
            and is_simple_expression(node.left, row_name)
            and is_simple_expression(node.right, row_name)
        )
    if isinstance(node, ast.UnaryOp):
        return is_simple_expression(node.operand, row_name)
    return False


# ---------------------------------------------------------------------------
# Rule 1: for i, row in df.iterrows(): df.at[i, "col"] = <math on row>
# ---------------------------------------------------------------------------


def match_iterrows_header(loop):
    """For 'for INDEX, ROW in DF.iterrows():' return the three names, or None."""
    target = loop.target
    if not (isinstance(target, ast.Tuple) and len(target.elts) == 2):
        return None
    index_var, row_var = target.elts
    if not (isinstance(index_var, ast.Name) and isinstance(row_var, ast.Name)):
        return None

    call = loop.iter
    if not (
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "iterrows"
        and isinstance(call.func.value, ast.Name)
        and not call.args
    ):
        return None

    return index_var.id, row_var.id, call.func.value.id


def rewrite_iterrows_loop(loop):
    """Turn a simple iterrows() loop into one vectorized line, or return None."""
    names = match_iterrows_header(loop)
    if names is None:
        return None
    index_name, row_name, df_name = names

    if len(loop.body) != 1 or loop.orelse:
        return None
    stmt = loop.body[0]
    if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1):
        return None

    left = stmt.targets[0]
    if not (
        isinstance(left, ast.Subscript)
        and isinstance(left.value, ast.Attribute)
        and left.value.attr in ("at", "loc")
        and isinstance(left.value.value, ast.Name)
        and left.value.value.id == df_name
        and isinstance(left.slice, ast.Tuple)
        and len(left.slice.elts) == 2
    ):
        return None

    row_key, column = left.slice.elts
    if not (
        isinstance(row_key, ast.Name)
        and row_key.id == index_name
        and isinstance(column, ast.Constant)
        and isinstance(column.value, str)
    ):
        return None

    if not is_simple_expression(stmt.value, row_name):
        return None

    new_value = RowToColumn(row_name, df_name).visit(stmt.value)
    new_target = ast.Subscript(
        value=ast.Name(id=df_name, ctx=ast.Load()),
        slice=ast.Constant(value=column.value),
        ctx=ast.Store(),
    )
    new_stmt = ast.Assign(targets=[new_target], value=new_value)
    return ast.fix_missing_locations(new_stmt)


# ---------------------------------------------------------------------------
# Rule 2: df["col"] = df.apply(lambda row: <math on row>, axis=1)
# ---------------------------------------------------------------------------


def rewrite_apply_assign(stmt):
    """Turn df["col"] = df.apply(lambda row: ..., axis=1) into column math, or return None."""
    if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1):
        return None
    call = stmt.value
    if not (
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "apply"
        and isinstance(call.func.value, ast.Name)
        and len(call.args) == 1
        and isinstance(call.args[0], ast.Lambda)
    ):
        return None
    df_name = call.func.value.id

    if not (
        len(call.keywords) == 1
        and call.keywords[0].arg == "axis"
        and isinstance(call.keywords[0].value, ast.Constant)
        and call.keywords[0].value.value in (1, "columns")
    ):
        return None

    lam = call.args[0]
    if not (len(lam.args.args) == 1 and not lam.args.defaults):
        return None
    row_name = lam.args.args[0].arg

    target = stmt.targets[0]
    if not (
        isinstance(target, ast.Subscript)
        and isinstance(target.value, ast.Name)
        and target.value.id == df_name
        and isinstance(target.slice, ast.Constant)
        and isinstance(target.slice.value, str)
    ):
        return None

    if not is_simple_expression(lam.body, row_name):
        return None

    new_value = RowToColumn(row_name, df_name).visit(lam.body)
    new_stmt = ast.Assign(targets=[target], value=new_value)
    return ast.fix_missing_locations(new_stmt)


# ---------------------------------------------------------------------------
# Shared helper for rules 3 and 4: TARGET = SERIES.apply(lambda x: BODY)
# ---------------------------------------------------------------------------


def match_series_lambda(stmt):
    """For 'TARGET = SERIES.apply(lambda x: BODY)' return the four parts, or None."""
    if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1):
        return None
    call = stmt.value
    if not (
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr in ("apply", "map")
        and len(call.args) == 1
        and isinstance(call.args[0], ast.Lambda)
        and not call.keywords
    ):
        return None
    lam = call.args[0]
    if not (len(lam.args.args) == 1 and not lam.args.defaults):
        return None
    return stmt.targets[0], call.func.value, lam.args.args[0].arg, lam.body


# ---------------------------------------------------------------------------
# Rule 3: SERIES.apply(lambda x: x.upper())  ->  SERIES.str.upper()
# ---------------------------------------------------------------------------

STRING_METHODS = (
    "upper", "lower", "title", "capitalize", "swapcase", "strip", "lstrip",
    "rstrip", "replace", "startswith", "endswith", "zfill",
)


def rewrite_string_lambda(stmt):
    """Turn SERIES.apply(lambda x: x.upper()) into SERIES.str.upper(), or return None."""
    parts = match_series_lambda(stmt)
    if parts is None:
        return None
    target, series, value_name, body = parts
    if not (
        isinstance(body, ast.Call)
        and isinstance(body.func, ast.Attribute)
        and body.func.attr in STRING_METHODS
        and isinstance(body.func.value, ast.Name)
        and body.func.value.id == value_name
        and not body.keywords
        and all(isinstance(arg, ast.Constant) for arg in body.args)
    ):
        return None
    str_accessor = ast.Attribute(value=series, attr="str", ctx=ast.Load())
    method = ast.Attribute(value=str_accessor, attr=body.func.attr, ctx=ast.Load())
    new_value = ast.Call(func=method, args=body.args, keywords=[])
    return ast.fix_missing_locations(ast.Assign(targets=[target], value=new_value))


# ---------------------------------------------------------------------------
# Rule 4: SERIES.apply(lambda x: lookup[x])  ->  SERIES.map(lookup)
# ---------------------------------------------------------------------------


def rewrite_dict_lambda(stmt):
    """Turn SERIES.apply(lambda x: lookup[x]) into SERIES.map(lookup), or return None."""
    parts = match_series_lambda(stmt)
    if parts is None:
        return None
    target, series, value_name, body = parts
    if not (
        isinstance(body, ast.Subscript)
        and isinstance(body.value, ast.Name)
        and body.value.id != value_name
        and isinstance(body.slice, ast.Name)
        and body.slice.id == value_name
    ):
        return None
    map_method = ast.Attribute(value=series, attr="map", ctx=ast.Load())
    new_value = ast.Call(func=map_method, args=[body.value], keywords=[])
    return ast.fix_missing_locations(ast.Assign(targets=[target], value=new_value))


# ---------------------------------------------------------------------------
# Rule 5: for x in items: result = pd.concat([result, piece])
#         ->  result = pd.concat([result] + [piece for x in items])
# ---------------------------------------------------------------------------


def uses_name(node, name):
    """Return True if the variable 'name' appears anywhere inside node."""
    return any(isinstance(n, ast.Name) and n.id == name for n in ast.walk(node))


def rewrite_concat_loop(loop):
    """Combine pd.concat calls inside a loop into one pd.concat call, or return None."""
    if len(loop.body) != 1 or loop.orelse:
        return None
    stmt = loop.body[0]
    if not (
        isinstance(stmt, ast.Assign)
        and len(stmt.targets) == 1
        and isinstance(stmt.targets[0], ast.Name)
    ):
        return None
    result_name = stmt.targets[0].id

    call = stmt.value
    if not (
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "concat"
        and len(call.args) == 1
        and isinstance(call.args[0], ast.List)
        and len(call.args[0].elts) == 2
    ):
        return None

    first, piece = call.args[0].elts
    if not (isinstance(first, ast.Name) and first.id == result_name):
        return None
    if uses_name(piece, result_name) or uses_name(loop.iter, result_name):
        return None

    pieces = ast.ListComp(
        elt=piece,
        generators=[ast.comprehension(target=loop.target, iter=loop.iter, ifs=[], is_async=0)],
    )
    all_parts = ast.BinOp(
        left=ast.List(elts=[ast.Name(id=result_name, ctx=ast.Load())], ctx=ast.Load()),
        op=ast.Add(),
        right=pieces,
    )
    new_call = ast.Call(func=call.func, args=[all_parts], keywords=call.keywords)
    return ast.fix_missing_locations(ast.Assign(targets=stmt.targets, value=new_call))


# ---------------------------------------------------------------------------
# Applying all the rules to a whole piece of code
# ---------------------------------------------------------------------------

LOOP_RULES = (rewrite_iterrows_loop, rewrite_concat_loop)
LINE_RULES = (rewrite_apply_assign, rewrite_string_lambda, rewrite_dict_lambda)


class LoopRewriter(ast.NodeTransformer):
    """Find every rewritable loop or line and remember its replacement."""

    def __init__(self):
        self.changes = []

    def visit_For(self, node):
        changes_before = len(self.changes)
        self.generic_visit(node)
        for rule in LOOP_RULES:
            new_stmt = rule(node)
            if new_stmt is not None:
                del self.changes[changes_before:]
                self.changes.append((node.lineno, node.end_lineno, ast.unparse(new_stmt)))
                return new_stmt
        return node

    def visit_Assign(self, node):
        for rule in LINE_RULES:
            new_stmt = rule(node)
            if new_stmt is not None:
                self.changes.append((node.lineno, node.end_lineno, ast.unparse(new_stmt)))
                return new_stmt
        return node


def rewrite_code(code):
    """Replace only the slow lines, keeping comments and formatting."""
    tree = ast.parse(code)
    rewriter = LoopRewriter()
    rewriter.visit(tree)

    lines = code.splitlines()
    for start, end, new_text in sorted(rewriter.changes, reverse=True):
        original = lines[start - 1]
        indent = original[: len(original) - len(original.lstrip())]
        lines[start - 1 : end] = [indent + new_text]

    changed_lines = [change[0] for change in rewriter.changes]
    return "\n".join(lines), changed_lines