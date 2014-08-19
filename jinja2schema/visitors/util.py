# coding: utf-8
"""
jinja2schema.visitors.util
~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
import jinja2.nodes

from ..mergers import merge
from ..model import Dictionary, Scalar, Unknown


def visit(node, config, predicted_struct_class=Scalar, return_struct_cls=Unknown, return_struct_possible_types=None,
          predicted_struct_possible_types=None):
    if isinstance(node, jinja2.nodes.Stmt):
        structure = visit_stmt(node, config)
    elif isinstance(node, jinja2.nodes.Expr):
        ctx = Context(predicted_struct=predicted_struct_class.from_ast(node, possible_types=predicted_struct_possible_types),
                      return_struct_cls=return_struct_cls,
                      return_struct_possible_types=return_struct_possible_types)
        _, structure = visit_expr(node, ctx, config)
    elif isinstance(node, jinja2.nodes.Template):
        structure = visit_many(node.body, config)
    return structure


def visit_many(nodes, config, predicted_struct_class=Scalar,
               return_struct_cls=Unknown, return_struct_possible_types=None, predicted_struct_possible_types=None):
    """Visits ``nodes`` and merges results.

    :param nodes: list of :class:`jinja2.nodes.Node`
    :param predicted_struct_class: ``predicted_struct`` for expression visitors will be constructed
                                   using this class by calling :meth:`from_ast` method
    :return: :class:`Dictionary`
    """
    rv = Dictionary()
    for node in nodes:
        structure = visit(node, config,
                          predicted_struct_class=predicted_struct_class,
                          return_struct_cls=return_struct_cls,
                          return_struct_possible_types=return_struct_possible_types,
                          predicted_struct_possible_types=predicted_struct_possible_types)
        rv = merge(rv, structure)
    return rv


# keep these at the end of file to avoid circular imports
from .expr import Context, visit_expr
from .stmt import visit_stmt
