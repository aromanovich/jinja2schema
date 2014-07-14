# coding: utf-8
"""
jinja2schema.visitors.util
~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
import jinja2.nodes

from ..mergers import merge
from ..model import Dictionary, Scalar


def visit(node, predicted_struct_class=Scalar):
    if isinstance(node, jinja2.nodes.Stmt):
        structure = visit_stmt(node)
    elif isinstance(node, jinja2.nodes.Expr):
        ctx = Context(predicted_struct=predicted_struct_class.from_ast(node))
        _, structure = visit_expr(node, ctx)
    elif isinstance(node, jinja2.nodes.Template):
        structure = visit_many(node.body)
    return structure


def visit_many(nodes, predicted_struct_class=Scalar):
    """Visits ``nodes`` and merges results.

    :param nodes: list of :class:`jinja2.nodes.Node`
    :param predicted_struct_class: ``predicted_struct`` for expression visitors will be constructed
                                   using this class by calling :meth:`from_ast` method
    :return: :class:`Dictionary`
    """
    rv = Dictionary()
    for node in nodes:
        structure = visit(node, predicted_struct_class=predicted_struct_class)
        rv = merge(rv, structure)
    return rv


# at the end to avoid circular imports
from .expr import Context, visit_expr
from .stmt import visit_stmt
