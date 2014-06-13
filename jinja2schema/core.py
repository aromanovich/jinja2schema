"""
There are two types of visitors, expression and statement.

Expression visitors return tuple which contains expression type and expression structure.

Statement visitors return :class:`.models.Dictionary` which contains
structures of variables used within the statement.
"""
import functools
import itertools

import jinja2
from jinja2 import nodes

from .model import Scalar, Dictionary, List, Unknown, Tuple


class Context(object):
    def __init__(self, rtype_cls=Scalar, inner_struct=None):
        self.rtype_cls = rtype_cls
        self.inner_struct = inner_struct

    def get_current_rtype(self, ast):
        return self.rtype_cls(linenos=[ast.lineno])

    def get_current_inner_struct(self, ast):
        return self.inner_struct if self.inner_struct else self.get_current_rtype(ast)


class MergeException(Exception):
    def __init__(self, fst, snd):
        self.fst = fst
        self.snd = snd


class UnsupportedSyntax(Exception):
    def __init__(self, ast, message):
        self.ast = ast
        self.message = message


def merge(fst, snd):
    assert (not (fst.linenos and snd.linenos) or
            max(fst.linenos) <= min(snd.linenos))

    if isinstance(fst, Unknown):
        result = snd
    elif isinstance(snd, Unknown):
        result = fst
    elif isinstance(fst, Scalar) and isinstance(snd, Scalar):
        result = Scalar()
    elif isinstance(fst, Dictionary) and isinstance(snd, Dictionary):
        result = Dictionary()
        for k in set(itertools.chain(fst.iterkeys(), snd.iterkeys())):
            if k in fst and k in snd:
                result[k] = merge(fst[k], snd[k])
            elif k in fst:
                result[k] = fst[k]
            elif k in snd:
                result[k] = snd[k]
    elif isinstance(fst, List) and isinstance(snd, List):
        result = List(merge(fst.el_struct, snd.el_struct))
    elif isinstance(fst, Tuple) and isinstance(snd, Tuple):
        if len(fst.el_structs) != len(snd.el_structs):
            raise MergeException(fst, snd)
        result = Tuple([merge(a, b) for a, b in zip(fst.el_structs, snd.el_structs)])
    else:
        raise MergeException(fst, snd)
    result.linenos = list(sorted(set(fst.linenos + snd.linenos)))
    result.constant = fst.constant
    result.may_be_defined = fst.may_be_defined
    return result


def merge_rtypes(fst, snd, operator=None):
    # TODO
    if isinstance(fst, Scalar) and not isinstance(snd, Scalar):
        return snd
    elif isinstance(snd, Scalar) and not isinstance(fst, Scalar):
        return fst
    return fst


stmt_visitors = {}
expr_visitors = {}


def visits_stmt(node_cls):
    def decorator(func):
        stmt_visitors[node_cls] = func
        @functools.wraps(func)
        def wrapped_func(ast, ctx):
            assert isinstance(ast, node_cls)
            return func(ast, ctx)
        return wrapped_func
    return decorator


def visits_expr(node_cls):
    def decorator(func):
        expr_visitors[node_cls] = func
        @functools.wraps(func)
        def wrapped_func(ast, ctx):
            assert isinstance(ast, node_cls)
            return func(ast, ctx)
        return wrapped_func
    return decorator


@visits_expr(nodes.BinExpr)
def visit_bin_expr(ast, ctx):
    l_rtype, l_struct = visit_expr(ast.left, ctx)
    r_rtype, r_struct = visit_expr(ast.right, ctx)
    return merge_rtypes(l_rtype, r_rtype, operator=ast.operator), merge(l_struct, r_struct)


@visits_expr(nodes.UnaryExpr)
def visit_unary_expr(ast, ctx):
    return visit_expr(ast.node, ctx)


@visits_expr(nodes.Compare)
def visit_compare(ast, ctx):
    rtype, struct = visit_expr(ast.expr, ctx)
    for op in ast.ops:
        op_rtype, op_struct = visit_expr(op.expr, ctx)
        rtype = merge_rtypes(rtype, op_rtype, operator=op.op)
        struct = merge(struct, op_struct)
    return rtype, struct


@visits_expr(nodes.Slice)
def visit_slice(ast, ctx):
    nodes = [node for node in [ast.start, ast.stop, ast.step] if node is not None]
    return Unknown(), visit_nodes_and_merge(nodes, Context(rtype_cls=Scalar))


@visits_expr(nodes.Getitem)
def visit_getitem(ast, ctx):
    curr_struct = ctx.get_current_inner_struct(ast)
    arg = ast.arg
    if isinstance(arg, nodes.Const):
        if isinstance(arg.value, int):
            inner_struct = List(curr_struct, linenos=[arg.lineno])
        elif isinstance(arg.value, basestring):
            inner_struct = Dictionary({arg.value: curr_struct}, lineno=[arg.lineno])
        else:
            raise UnsupportedSyntax(arg, '{} is not supported as an index for a list or'
                                         ' a key for a dictionary'.format(arg.value))
    else:
        inner_struct = List(curr_struct, linenos=[arg.lineno])
    arg_rtype, arg_struct = visit_expr(arg, Context(rtype_cls=Scalar))
    rtype, struct = visit_expr(ast.node, Context(rtype_cls=ctx.rtype_cls,
                                                 inner_struct=inner_struct))
    return rtype, merge(struct, arg_struct)


@visits_expr(nodes.Getattr)
def visit_getattr(ast, ctx):
    context = Context(
        rtype_cls=ctx.rtype_cls,
        inner_struct=Dictionary({
            ast.attr: ctx.get_current_inner_struct(ast),
        }, linenos=[ast.lineno]))
    return visit_expr(ast.node, context)


@visits_expr(nodes.Test)
def visit_test(ast, ctx):
    # todo type assertion
    return visit_expr(ast.node, ctx)


@visits_expr(nodes.Name)
def visit_name(ast, ctx):
    return ctx.get_current_rtype(ast), Dictionary({
        ast.name: ctx.get_current_inner_struct(ast)
    })


@visits_expr(nodes.Concat)
def visit_concat(ast, ctx):
    return Scalar(), visit_nodes_and_merge(ast.nodes, ctx)


@visits_expr(nodes.CondExpr)
def visit_cond_expr(ast, ctx):
    test_rtype, test_struct = visit_expr(ast.test, Context(rtype_cls=Unknown))
    if_rtype, if_struct = visit_expr(ast.expr1, ctx)
    else_rtype, else_struct = visit_expr(ast.expr2, ctx)
    struct = merge(merge(if_struct, test_struct), else_struct)
    rtype = merge_rtypes(if_rtype, else_rtype)

    if isinstance(ast.test, nodes.Test) and isinstance(ast.test.node, nodes.Name):
        if ast.test.name in ('defined', 'undefined'):
            rtype.may_be_defined = True
    return rtype, struct


# :class:`nodes.Literal` visitors

@visits_expr(nodes.TemplateData)
def visit_template_data(ast, ctx):
    return Scalar(), Dictionary()


@visits_expr(nodes.Const)
def visit_const(ast, ctx):
    return Scalar(linenos=[ast.lineno], constant=True), Dictionary()


@visits_expr(nodes.Tuple)
def visit_tuple(ast, ctx):
    struct = Dictionary()

    rtypes = []
    for item in ast.items:
        item_rtype, item_struct = visit_expr(item, ctx)
        rtypes.append(item_rtype)
        struct = merge(struct, item_struct)

    return Tuple(rtypes, linenos=[ast.lineno], constant=True), struct


@visits_expr(nodes.List)
def visit_list(ast, ctx):
    struct = Dictionary()

    el_rtype = None
    for item in ast.items:
        item_rtype, item_struct = visit_expr(item, Context())
        struct = merge(struct, item_struct)
        if el_rtype is None:
            el_rtype = item_rtype
        else:
            el_rtype = merge_rtypes(el_rtype, item_rtype)
    rtype = List(el_rtype, linenos=[ast.lineno], constant=True)
    return rtype, struct


@visits_expr(nodes.Dict)
def visit_dict(ast, ctx):
    rtype = Dictionary(linenos=[ast.lineno], constant=True)
    struct = Dictionary()
    for item in ast.items:
        key_rtype, key_struct = visit_expr(item.key, Context(rtype_cls=Scalar))
        struct = merge(struct, key_struct)
        assert isinstance(key_rtype, Scalar)
        value_rtype, value_struct = visit_expr(item.value, ctx)
        struct = merge(struct, value_struct)
        if isinstance(item.key, nodes.Const):
            rtype[item.key.value] = value_rtype
    return rtype, struct


# Statement visitors

@visits_stmt(nodes.For)
def visit_for(ast, ctx):
    body_struct = visit_nodes_and_merge(ast.body, ctx)
    else_struct = visit_nodes_and_merge(ast.else_, ctx)
    if 'loop' in body_struct:
        # exclude a special `loop` variable from the body structure
        del body_struct['loop']
    if isinstance(ast.target, nodes.Tuple):
        target_struct = Tuple([body_struct.pop(item.name, Unknown(linenos=[ast.target.lineno]))
                               for item in ast.target.items],
                              linenos=[ast.target.lineno])
    else:
        target_struct = body_struct.pop(ast.target.name, Unknown(linenos=[ast.target.lineno]))
    context = Context(rtype_cls=Unknown, inner_struct=List(target_struct, linenos=[ast.lineno]))
    return merge(merge(visit(ast.iter, context), body_struct), else_struct)


@visits_stmt(nodes.If)
def visit_if(ast, ctx):
    test_rtype, test_struct = visit_expr(ast.test, Context(rtype_cls=Unknown))
    if_struct = visit_nodes_and_merge(ast.body, ctx)
    else_struct = visit_nodes_and_merge(ast.else_, ctx) if ast.else_ else Dictionary()
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
def visit_assign(ast, ctx):
    struct = Dictionary()
    if (isinstance(ast.target, nodes.Name) or
            (isinstance(ast.target, nodes.Tuple) and isinstance(ast.node, nodes.Tuple))):
        context = Context(rtype_cls=Unknown)
        variables = []
        if isinstance(ast.target, nodes.Name):
            variables.append((ast.target.name, ast.node))
        else:
            if len(ast.target.items) != len(ast.node.items):
                raise UnsupportedSyntax(ast, 'number of items in left side is different '
                                             'from right side')
            for name_ast, var_ast in itertools.izip(ast.target.items, ast.node.items):
                variables.append((name_ast.name, var_ast))
        for var_name, var_ast in variables:
            var_rtype, var_struct = visit_expr(var_ast, context)
            var_rtype.constant = True
            struct = merge(merge(struct, var_struct), Dictionary({
                var_name: var_rtype,
            }))
        return struct
    elif isinstance(ast.target, nodes.Tuple):
        tuple_items = []
        for name_ast in ast.target.items:
            var_struct = Unknown(lineno=[name_ast.lineno], constant=True)
            tuple_items.append(var_struct)
            struct = merge(struct, Dictionary({name_ast.name: var_struct}))
        var_rtype, var_struct = visit_expr(
            ast.node, Context(rtype_cls=lambda **kw: Tuple(tuple_items, **kw)))
        return merge(struct, var_struct)
    else:
        raise UnsupportedSyntax(ast, 'unsupported assignment')


@visits_stmt(nodes.Output)
def visit_output(ast, ctx):
    return visit_nodes_and_merge(ast.nodes, ctx)


@visits_stmt(nodes.Template)
def visit_template(ast, ctx):
    return visit_nodes_and_merge(ast.body, ctx)


def visit_nodes_and_merge(nodes, ctx):
    rv = Dictionary()
    for node in nodes:
        rv = merge(rv, visit(node, ctx))
    return rv


def visit_stmt(ast, ctx):
    visitor = stmt_visitors.get(type(ast))
    if not visitor:
        for node_cls, visitor_ in stmt_visitors.iteritems():
            if isinstance(ast, node_cls):
                visitor = visitor_
    if not visitor:
        raise Exception('stmt visitor for {} is not found'.format(type(ast)))
    rv = visitor(ast, ctx)
    assert isinstance(rv, Dictionary)
    return rv


def visit_expr(ast, ctx):
    import inspect
    visitor = expr_visitors.get(type(ast))
    if not visitor:
        for node_cls, visitor_ in expr_visitors.iteritems():
            if isinstance(ast, node_cls):
                visitor = visitor_
    if not visitor:
        raise Exception('expr visitor for {} is not found'.format(type(ast)))
    rv = visitor(ast, ctx)
    return rv


def visit(ast, ctx):
    if isinstance(ast, nodes.Stmt):
        structure = visit_stmt(ast, ctx)
    elif isinstance(ast, nodes.Expr):
        rtype, structure = visit_expr(ast, ctx)
    return structure


def _post_process(struct):
    if isinstance(struct, Dictionary):
        for k, v in struct.items():
            if v.constant and not v.may_be_defined:
                del struct[k]
            else:
                _post_process(v)
    return struct


def infer(ast):
    """
    :type ast: :class:`nodes.Template`
    """
    rv = visit_nodes_and_merge(ast.body, Context())
    return _post_process(rv)


def parse(template):
    jinja2_env = jinja2.Environment()
    ast = jinja2_env.parse(template)
    return ast
