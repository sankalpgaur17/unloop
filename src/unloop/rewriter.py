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