# coding: utf-8
"""
jinja2schema.visitors.stmt
~~~~~~~~~~~~~~~~~~~~~~~~~~

Statement is an instance of :class:`jinja2.nodes.Stmt`.
Statement visitors return :class:`.models.Dictionary` of structures of variables used within the statement.
"""
import functools

from jinja2 import nodes

from ..model import Scalar, Dictionary, List, Unknown, Tuple, Boolean
from ..mergers import merge
from ..exceptions import InvalidExpression
from .. import _compat
from .expr import Context, visit_expr
from .util import visit_many


stmt_visitors = {}


def visits_stmt(node_cls):
    """Decorator that registers a function as a visitor for ``node_cls``.

    :param node_cls: subclass of :class:`jinja2.nodes.Stmt`
    """
    def decorator(func):
        stmt_visitors[node_cls] = func
        @functools.wraps(func)
        def wrapped_func(ast, config):
            assert isinstance(ast, node_cls)
            return func(ast, config)
        return wrapped_func
    return decorator


def visit_stmt(ast, config):
    """Returns a structure of ``ast``.

    :param ast: instance of :class:`jinja2.nodes.Stmt`
    :returns: :class:`.model.Dictionary`
    """
    visitor = stmt_visitors.get(type(ast))
    if not visitor:
        for node_cls, visitor_ in stmt_visitors.iteritems():
            if isinstance(ast, node_cls):
                visitor = visitor_
    if not visitor:
        raise Exception('stmt visitor for {} is not found'.format(type(ast)))
    return visitor(ast, config)


@visits_stmt(nodes.For)
def visit_for(ast, config):
    body_struct = visit_many(ast.body, config, predicted_struct_cls=Scalar)
    else_struct = visit_many(ast.else_, config, predicted_struct_cls=Scalar)

    if 'loop' in body_struct:
        # exclude a special `loop` variable from the body structure
        del body_struct['loop']

    if isinstance(ast.target, nodes.Tuple):
        target_struct = Tuple.from_ast(
            ast.target,
            [body_struct.pop(item.name, Unknown.from_ast(ast.target))
             for item in ast.target.items])
    else:
        target_struct = body_struct.pop(ast.target.name, Unknown.from_ast(ast))

    iter_rtype, iter_struct = visit_expr(
        ast.iter,
        Context(
            return_struct_cls=Unknown,
            predicted_struct=List.from_ast(ast, target_struct)),
        config)

    merge(iter_rtype, List(target_struct))

    return merge(merge(iter_struct, body_struct), else_struct)


@visits_stmt(nodes.If)
def visit_if(ast, config):
    if config.ALLOW_ONLY_BOOLEAN_VARIABLES_IN_TEST:
        test_predicted_struct = Boolean.from_ast(ast.test)
    else:
        test_predicted_struct = Unknown.from_ast(ast.test)
    test_rtype, test_struct = visit_expr(
        ast.test, Context(return_struct_cls=Unknown, predicted_struct=test_predicted_struct), config)
    if_struct = visit_many(ast.body, config, predicted_struct_cls=Scalar)
    else_struct = visit_many(ast.else_, config, predicted_struct_cls=Scalar) if ast.else_ else Dictionary()
    struct = merge(merge(test_struct, if_struct), else_struct)

    if isinstance(ast.test, nodes.Test) and isinstance(ast.test.node, nodes.Name):
        lookup_struct = None
        if ast.test.name == 'undefined':
            lookup_struct = if_struct
        if ast.test.name == 'defined':
            lookup_struct = else_struct
        var_name = ast.test.node.name
        if lookup_struct is not None and var_name in lookup_struct:
            struct[var_name].may_be_defined = True
    return struct


@visits_stmt(nodes.Assign)
def visit_assign(ast, config):
    struct = Dictionary()
    if (isinstance(ast.target, nodes.Name) or
            (isinstance(ast.target, nodes.Tuple) and isinstance(ast.node, nodes.Tuple))):
        variables = []
        if not (isinstance(ast.target, nodes.Tuple) and isinstance(ast.node, nodes.Tuple)):
            variables.append((ast.target.name, ast.node))
        else:
            if len(ast.target.items) != len(ast.node.items):
                raise InvalidExpression(ast, 'number of items in left side is different '
                                             'from right side')
            for name_ast, var_ast in _compat.izip(ast.target.items, ast.node.items):
                variables.append((name_ast.name, var_ast))
        for var_name, var_ast in variables:
            var_rtype, var_struct = visit_expr(var_ast, Context(predicted_struct=Unknown.from_ast(var_ast)), config)
            var_rtype.constant = True
            var_rtype.label = var_name
            struct = merge(merge(struct, var_struct), Dictionary({
                var_name: var_rtype,
            }))
        return struct
    elif isinstance(ast.target, nodes.Tuple):
        tuple_items = []
        for name_ast in ast.target.items:
            var_struct = Unknown.from_ast(name_ast, constant=True)
            tuple_items.append(var_struct)
            struct = merge(struct, Dictionary({name_ast.name: var_struct}))
        var_rtype, var_struct = visit_expr(
            ast.node, Context(return_struct_cls=Unknown, predicted_struct=Tuple(tuple_items)), config)
        return merge(struct, var_struct)
    else:
        raise InvalidExpression(ast, 'unsupported assignment')


@visits_stmt(nodes.Output)
def visit_output(ast, config):
    return visit_many(ast.nodes, config, predicted_struct_cls=Scalar)
