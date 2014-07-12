import functools

import jinja2.nodes

from ..mergers import merge
from ..model import Dictionary
from ..context import Context


stmt_visitors = {}


def visits_stmt(node_cls):
    def decorator(func):
        stmt_visitors[node_cls] = func
        @functools.wraps(func)
        def wrapped_func(ast):
            assert isinstance(ast, node_cls)
            return func(ast)
        return wrapped_func
    return decorator


def visit_stmt(ast):
    visitor = stmt_visitors.get(type(ast))
    if not visitor:
        for node_cls, visitor_ in stmt_visitors.iteritems():
            if isinstance(ast, node_cls):
                visitor = visitor_
    if not visitor:
        raise Exception('stmt visitor for {} is not found'.format(type(ast)))
    return visitor(ast)


expr_visitors = {}


def visits_expr(node_cls):
    def decorator(func):
        expr_visitors[node_cls] = func
        @functools.wraps(func)
        def wrapped_func(ast, ctx):
            assert isinstance(ast, node_cls)
            return func(ast, ctx)
        return wrapped_func
    return decorator


def visit_expr(ast, ctx):
    visitor = expr_visitors.get(type(ast))
    if not visitor:
        for node_cls, visitor_ in expr_visitors.iteritems():
            if isinstance(ast, node_cls):
                visitor = visitor_
    if not visitor:
        raise Exception('expr visitor for {} is not found'.format(type(ast)))
    return visitor(ast, ctx)


def visit_many(ast_nodes, predicted_struct_class):
    rv = Dictionary()
    for node in ast_nodes:
        if isinstance(node, jinja2.nodes.Stmt):
            structure = visit_stmt(node)
        elif isinstance(node, jinja2.nodes.Expr):
            ctx = Context(predicted_struct=predicted_struct_class.from_ast(node))
            _, structure = visit_expr(node, ctx)
        rv = merge(rv, structure)
    return rv


from . import expr, stmt
