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