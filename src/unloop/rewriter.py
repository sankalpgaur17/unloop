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