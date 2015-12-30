# coding: utf-8
"""
jinja2schema.visitors.stmt
~~~~~~~~~~~~~~~~~~~~~~~~~~

Statement is an instance of :class:`jinja2.nodes.Stmt`.
Statement visitors return :class:`.models.Dictionary` of structures of variables used within the statement.
"""
import functools

from jinja2 import nodes, Environment, PackageLoader
from jinja2schema.config import default_config

from ..model import Scalar, Dictionary, List, Unknown, Tuple, Boolean
from ..macro import Macro
from ..mergers import merge, merge_many
from ..exceptions import InvalidExpression
from .._compat import iteritems, izip, zip_longest
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
        def wrapped_func(ast, macroses=None, config=default_config, child_blocks=None):
            assert isinstance(ast, node_cls)
            return func(ast, macroses, config, child_blocks)
        return wrapped_func
    return decorator


def visit_stmt(ast, macroses=None, config=default_config, child_blocks=None):
    """Returns a structure of ``ast``.

    :param ast: instance of :class:`jinja2.nodes.Stmt`
    :returns: :class:`.model.Dictionary`
    """
    visitor = stmt_visitors.get(type(ast))
    if not visitor:
        for node_cls, visitor_ in iteritems(stmt_visitors):
            if isinstance(ast, node_cls):
                visitor = visitor_
    if not visitor:
        raise Exception('stmt visitor for {0} is not found'.format(type(ast)))
    return visitor(ast, macroses, config)


@visits_stmt(nodes.For)
def visit_for(ast, macroses=None, config=default_config, child_blocks=None):
    body_struct = visit_many(ast.body, macroses, config, predicted_struct_cls=Scalar)
    else_struct = visit_many(ast.else_, macroses, config, predicted_struct_cls=Scalar)

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
        macroses, config)

    merge(iter_rtype, List(target_struct))

    return merge_many(iter_struct, body_struct, else_struct)


@visits_stmt(nodes.If)
def visit_if(ast, macroses=None, config=default_config, child_blocks=None):
    if config.BOOLEAN_CONDITIONS:
        test_predicted_struct = Boolean.from_ast(ast.test)
    else:
        test_predicted_struct = Unknown.from_ast(ast.test)
    test_rtype, test_struct = visit_expr(
        ast.test, Context(predicted_struct=test_predicted_struct), macroses, config)
    if_struct = visit_many(ast.body, macroses, config, predicted_struct_cls=Scalar)
    else_struct = visit_many(ast.else_, macroses, config, predicted_struct_cls=Scalar) if ast.else_ else Dictionary()
    struct = merge_many(test_struct, if_struct, else_struct)

    for var_name, var_struct in iteritems(test_struct):
        if var_struct.checked_as_defined or var_struct.checked_as_undefined:
            if var_struct.checked_as_undefined:
                lookup_struct = if_struct
            elif var_struct.checked_as_defined:
                lookup_struct = else_struct
            struct[var_name].may_be_defined = (lookup_struct and
                                               var_name in lookup_struct and
                                               lookup_struct[var_name].constant)
            struct[var_name].checked_as_defined = test_struct[var_name].checked_as_defined and (
                not lookup_struct or not var_name in lookup_struct or lookup_struct[var_name].constant
            )
            struct[var_name].checked_as_undefined = test_struct[var_name].checked_as_undefined and (
                not lookup_struct or not var_name in lookup_struct or lookup_struct[var_name].constant
            )
    return struct


@visits_stmt(nodes.Assign)
def visit_assign(ast, macroses=None, config=default_config, child_blocks=None):
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
            for name_ast, var_ast in izip(ast.target.items, ast.node.items):
                variables.append((name_ast.name, var_ast))
        for var_name, var_ast in variables:
            var_rtype, var_struct = visit_expr(var_ast, Context(predicted_struct=Unknown.from_ast(var_ast)), macroses, config)
            var_rtype.constant = True
            var_rtype.label = var_name
            struct = merge_many(struct, var_struct, Dictionary({
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
            ast.node, Context(return_struct_cls=Unknown, predicted_struct=Tuple(tuple_items)), macroses, config)
        return merge(struct, var_struct)
    else:
        raise InvalidExpression(ast, 'unsupported assignment')


@visits_stmt(nodes.Output)
def visit_output(ast, macroses=None, config=default_config, child_blocks=None):
    return visit_many(ast.nodes, macroses, config, predicted_struct_cls=Scalar)


@visits_stmt(nodes.Macro)
def visit_macro(ast, macroses=None, config=default_config, child_blocks=None):
    # XXX the code needs to be refactored
    args = []
    kwargs = []
    body_struct = visit_many(ast.body, macroses, config, predicted_struct_cls=Scalar)

    for i, (arg, default_value_ast) in enumerate(reversed(list(zip_longest(reversed(ast.args),
                                                                           reversed(ast.defaults)))), start=1):
        has_default_value = bool(default_value_ast)
        if has_default_value:
            default_rtype, default_struct = visit_expr(
                default_value_ast, Context(predicted_struct=Unknown()), macroses, config)
        else:
            default_rtype = Unknown(linenos=[arg.lineno])
        default_rtype.constant = False
        default_rtype.label = 'argument "{0}"'.format(arg.name) if has_default_value else 'argument #{0}'.format(i)
        if arg.name in body_struct:
            default_rtype = merge(default_rtype, body_struct[arg.name])  # just to make sure
        default_rtype.linenos = [ast.lineno]
        if has_default_value:
            kwargs.append((arg.name, default_rtype))
        else:
            args.append((arg.name, default_rtype))
    macroses[ast.name] = Macro(ast.name, args, kwargs)

    tmp = dict(args)
    tmp.update(dict(kwargs))
    args_struct = Dictionary(tmp)
    for arg_name, arg_type in args:
        args_struct[arg_name] = arg_type

    for arg in args_struct.iterkeys():
        body_struct.pop(arg, None)
    return body_struct


@visits_stmt(nodes.Block)
def visit_block(ast, macroses=None, config=default_config):
    return visit_many(ast.body, macroses, config)


@visits_stmt(nodes.Include)
def visit_include(ast, macroses=None, config=default_config, child_blocks=None):
    template = get_inherited_template(config, ast)
    return visit_many(template.body, macroses, config)


@visits_stmt(nodes.Extends)
def visit_extends(ast, macroses=None, config=default_config, child_blocks=None):
    template = get_inherited_template(config, ast)
    if not child_blocks:
        return visit_many(template.body, macroses, config)
    return visit_many(get_correct_nodes(child_blocks, template.body), None, config)


def get_inherited_template(config, ast):
    env = Environment(loader=PackageLoader(config.PACKAGE_NAME, config.TEMPLATE_DIR))
    return env.parse(env.loader.get_source(env, ast.template.value)[0])


def separate_template_blocks(template, blocks, template_nodes):
    for node in template:
        if isinstance(node, nodes.Block):
            blocks.append(node)
        else:
            template_nodes.append(node)
    return blocks, template_nodes


def get_correct_nodes(child_blocks, template):
    parent_blocks, nodes = separate_template_blocks(template, [], [])
    child_block_names = [c.name for c in child_blocks]
    blocks = child_blocks + parent_blocks
    for parent_block in parent_blocks:
        if parent_block.name in child_block_names:
            blocks.remove(parent_block)
    return blocks + nodes
