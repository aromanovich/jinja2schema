# coding: utf-8
"""
jinja2schema.visitors.expr
~~~~~~~~~~~~~~~~~~~~~~~~~~

Expression is an instance of :class:`jinja2.nodes.Expr`.
Expression visitors return a tuple which contains expression type and expression structure.
"""
import functools

from jinja2 import nodes

from ..model import Scalar, Dictionary, List, Unknown, Tuple, String, Number, Boolean
from ..mergers import merge_rtypes, merge
from ..exceptions import InvalidExpression, UnexpectedExpression, MergeException
from .. import _compat
from .util import visit_many


class Context(object):
    """
    Context is used when parsing expressions.

    Suppose there is an expression::

        {{ data.field.subfield }}

    It has the following AST::

        Getattr(
            node=Getattr(
                node=Name(name='data')
                attr='field'
            ),
            attr='subfield'
        )

    :func:`visit_getattr` returns a pair that looks like this::

        (
            # return type:
            Scalar(...),
            # structure:
            {
                'data: {
                    'field': {
                        'subfield': Scalar(...)
                    }
                }
            }
        }

    The return type is defined by the outermost :class:`nodes.Getattr` node, which
    in this case is being printed.
    The structure is build during AST traversal from outer to inners nodes and it is
    kind of "reversed" in relation to the AST.
    :class:`Context` is intended for:

    * capturing a return type and passing it to the innermost expression node;
    * passing a structure "under construction" to the visitors of nested nodes.

    Let's look through an example.

    Suppose :func:`visit_getattr` is called with the following arguments::

       ast = Getattr(node=Getattr(node=Name(name='data'), attr='field'), attr='subfield'))
       context = Context(return_struct_cls=Scalar, predicted_struct=Scalar())

    It looks to the outermost AST node and based on it's type (which is :class:`nodes.Getattr`)
    and it's ``attr`` field (which equals to ``"subfield"``) infers that a variable described by the
    nested AST node must a dictionary with ``"subfield"`` key.

    It calls a visitor for inner node and :func:`visit_getattr` gets called again, but
    with different arguments::

       ast = Getattr(node=Name(name='data', ctx='load'), attr='field')
       ctx = Context(return_struct_cls=Scalar, predicted_struct=Dictionary({subfield: Scalar()}))

    :func:`visit_getattr` applies the same logic again. The inner node is a :class:`nodes.Name`, so that
    it calls :func:`visit_name` with the following arguments::

       ast = Name(name='data')
       ctx = Context(
           return_struct_cls=Scalar,
           predicted_struct=Dictionary({
               field: Dictionary({subfield: Scalar()}))
           })
       )

    :func:`visit_name` does not do much by itself. Based on a context it knows what structure and
    what type must have a variable described by a given :class:`nodes.Name` node, so
    it just returns a pair::

        (instance of context.return_struct_cls, Dictionary({data: context.predicted_struct}})
    """
    def __init__(self, ctx=None, return_struct_cls=None, predicted_struct=None):
        self.predicted_struct = None
        self.return_struct_cls = Unknown
        if ctx:
            self.predicted_struct = ctx.predicted_struct
            self.return_struct_cls = ctx.return_struct_cls
        if predicted_struct:
            self.predicted_struct = predicted_struct
        if return_struct_cls:
            self.return_struct_cls = return_struct_cls

    def get_predicted_struct(self, label=None):
        rv = self.predicted_struct.clone()
        if label:
            rv.label = label
        return rv

    def meet(self, actual_struct, actual_ast):
        try:
            merge(self.predicted_struct, actual_struct)
        except MergeException:
            raise UnexpectedExpression(self.predicted_struct, actual_ast, actual_struct)
        else:
            return True


expr_visitors = {}


def visits_expr(node_cls):
    """Decorator that registers a function as a visitor for ``node_cls``.

    :param node_cls: subclass of :class:`jinja2.nodes.Expr`
    """
    def decorator(func):
        expr_visitors[node_cls] = func
        @functools.wraps(func)
        def wrapped_func(ast, ctx, config):
            assert isinstance(ast, node_cls)
            return func(ast, ctx, config)
        return wrapped_func
    return decorator


def visit_expr(ast, ctx, config):
    """Returns a structure of ``ast``.

    :param ctx: :class:`Context`
    :param ast: instance of :class:`jinja2.nodes.Expr`
    :returns: a tuple where the first element is an expression type (instance of :class:`Variable`)
              and the second element is an expression structure (instance of :class:`.model.Dictionary`)
    """
    visitor = expr_visitors.get(type(ast))
    if not visitor:
        for node_cls, visitor_ in _compat.iteritems(expr_visitors):
            if isinstance(ast, node_cls):
                visitor = visitor_
    if not visitor:
        raise Exception('expression visitor for {} is not found'.format(type(ast)))
    return visitor(ast, ctx, config)


def _visit_dict(ast, ctx, items, config):
    """A common logic behind nodes.Dict and nodes.Call (``{{ dict(a=1) }}``)
    visitors.

    :param items: a list of (key, value); key may be either AST node or string
    """
    ctx.meet(Dictionary(), ast)
    rtype = Dictionary.from_ast(ast, constant=True)
    struct = Dictionary()
    for key, value in items:
        value_rtype, value_struct = visit_expr(value, Context(
            predicted_struct=Unknown.from_ast(value)), config)
        struct = merge(struct, value_struct)
        if isinstance(key, nodes.Node):
            key_rtype, key_struct = visit_expr(key, Context(predicted_struct=Scalar.from_ast(key)), config)
            struct = merge(struct, key_struct)
            if isinstance(key, nodes.Const):
                rtype[key.value] = value_rtype
        elif isinstance(key, _compat.string_types):
            rtype[key] = value_rtype
    return rtype, struct


@visits_expr(nodes.BinExpr)
def visit_bin_expr(ast, ctx, config):
    l_rtype, l_struct = visit_expr(ast.left, ctx, config)
    r_rtype, r_struct = visit_expr(ast.right, ctx, config)
    return merge_rtypes(l_rtype, r_rtype, operator=ast.operator), merge(l_struct, r_struct)


@visits_expr(nodes.UnaryExpr)
def visit_unary_expr(ast, ctx, config):
    return visit_expr(ast.node, ctx, config)


@visits_expr(nodes.Compare)
def visit_compare(ast, ctx, config):
    rtype, struct = visit_expr(ast.expr, ctx, config)
    for op in ast.ops:
        op_rtype, op_struct = visit_expr(op.expr, ctx, config)
        struct = merge(struct, op_struct)
    return Boolean.from_ast(ast), struct


@visits_expr(nodes.Slice)
def visit_slice(ast, ctx, config):
    nodes = [node for node in [ast.start, ast.stop, ast.step] if node is not None]
    struct = visit_many(nodes, config,
                        predicted_struct_cls=Number,
                        return_struct_cls=Number)
    return Unknown(), struct


@visits_expr(nodes.Name)
def visit_name(ast, ctx, config):
    kwargs = {}
    return ctx.return_struct_cls.from_ast(ast, **kwargs), Dictionary({
        ast.name: ctx.get_predicted_struct(label=ast.name)
    })


@visits_expr(nodes.Getattr)
def visit_getattr(ast, ctx, config):
    context = Context(
        ctx=ctx,
        predicted_struct=Dictionary.from_ast(ast, {
            ast.attr: ctx.get_predicted_struct(label=ast.attr),
        }))
    return visit_expr(ast.node, context, config)


@visits_expr(nodes.Getitem)
def visit_getitem(ast, ctx, config):
    arg = ast.arg
    if isinstance(arg, nodes.Const):
        if isinstance(arg.value, int):
            if config.TYPE_OF_VARIABLE_INDEXED_WITH_INTEGER_TYPE == 'list':
                predicted_struct = List.from_ast(ast, ctx.get_predicted_struct())
            elif config.TYPE_OF_VARIABLE_INDEXED_WITH_INTEGER_TYPE == 'dictionary':
                predicted_struct = Dictionary.from_ast(ast, {
                    arg.value: ctx.get_predicted_struct(),
                })
        elif isinstance(arg.value, _compat.string_types):
            predicted_struct = Dictionary.from_ast(ast, {
                arg.value: ctx.get_predicted_struct(label=arg.value),
            })
        else:
            raise InvalidExpression(arg, '{} is not supported as an index for a list or'
                                         ' a key for a dictionary'.format(arg.value))
    elif isinstance(arg, nodes.Slice):
        predicted_struct = List.from_ast(ast, ctx.get_predicted_struct())
    else:
        if config.TYPE_OF_VARIABLE_INDEXED_WITH_VARIABLE_TYPE == 'list':
            predicted_struct = List.from_ast(ast, ctx.get_predicted_struct())
        elif config.TYPE_OF_VARIABLE_INDEXED_WITH_VARIABLE_TYPE == 'dictionary':
            predicted_struct = Dictionary.from_ast(ast)

    _, arg_struct = visit_expr(arg, Context(predicted_struct=Scalar.from_ast(arg)), config)
    rtype, struct = visit_expr(ast.node, Context(
        ctx=ctx,
        predicted_struct=predicted_struct), config)
    return rtype, merge(struct, arg_struct)


@visits_expr(nodes.Test)
def visit_test(ast, ctx, config):
    if ast.name in ('divisibleby', 'escaped', 'even', 'lower', 'odd', 'upper'):
        ctx.meet(Scalar(), ast)
        predicted_struct = Scalar.from_ast(ast.node)
    elif ast.name in ('defined', 'undefined', 'equalto', 'iterable', 'mapping',
                      'none', 'number', 'sameas', 'sequence', 'string'):
        predicted_struct = Unknown.from_ast(ast.node)
    else:
        raise InvalidExpression(ast, 'unknown test "{}"'.format(ast.name))
    rtype, struct = visit_expr(ast.node, Context(return_struct_cls=Boolean,
                                                 predicted_struct=predicted_struct), config)
    if ast.name == 'divisibleby':
        if not ast.args:
            raise InvalidExpression(ast, 'divisibleby must have an argument')
        _, arg_struct = visit_expr(ast.args[0],
                                   Context(predicted_struct=Number.from_ast(ast.args[0])), config)
        struct = merge(arg_struct, struct)
    return rtype, struct


@visits_expr(nodes.Concat)
def visit_concat(ast, ctx, config):
    ctx.meet(Scalar(), ast)
    return String.from_ast(ast), \
           visit_many(ast.nodes, config, predicted_struct_cls=String)


@visits_expr(nodes.CondExpr)
def visit_cond_expr(ast, ctx, config):
    if config.ALLOW_ONLY_BOOLEAN_VARIABLES_IN_TEST:
        test_predicted_struct = Boolean.from_ast(ast.test)
    else:
        test_predicted_struct = Unknown.from_ast(ast.test)
    test_rtype, test_struct = visit_expr(ast.test, Context(predicted_struct=test_predicted_struct), config)
    if_rtype, if_struct = visit_expr(ast.expr1, ctx, config)
    else_rtype, else_struct = visit_expr(ast.expr2, ctx, config)
    struct = merge(merge(if_struct, test_struct), else_struct)
    rtype = merge_rtypes(if_rtype, else_rtype)

    if (isinstance(ast.test, nodes.Test) and isinstance(ast.test.node, nodes.Name) and
            ast.test.name in ('defined', 'undefined')):
        struct[ast.test.node.name].may_be_defined = True
    return rtype, struct


@visits_expr(nodes.Call)
def visit_call(ast, ctx, config):
    if isinstance(ast.node, nodes.Name):
        if ast.node.name == 'range':
            ctx.meet(List(Unknown()), ast)
            struct = Dictionary()
            for arg in ast.args:
                arg_rtype, arg_struct = visit_expr(arg, Context(
                    predicted_struct=Number.from_ast(arg)), config)
                struct = merge(struct, arg_struct)
            return List(Number()), struct
        elif ast.node.name == 'lipsum':
            ctx.meet(Scalar(), ast)
            struct = Dictionary()
            # perhaps TODO: set possible types for args and kwargs
            for arg in ast.args:
                arg_rtype, arg_struct = visit_expr(arg, Context(predicted_struct=Scalar.from_ast(arg)), config)
                struct = merge(struct, arg_struct)
            for kwarg in ast.kwargs:
                arg_rtype, arg_struct = visit_expr(kwarg.value, Context(predicted_struct=Scalar.from_ast(kwarg)), config)
                struct = merge(struct, arg_struct)
            return Scalar(), struct
        elif ast.node.name == 'dict':
            ctx.meet(Dictionary(), ast)
            if ast.args:
                raise InvalidExpression(ast, 'dict accepts only keyword arguments')
            return _visit_dict(ast, ctx, [(kwarg.key, kwarg.value) for kwarg in ast.kwargs], config)
        else:
            raise InvalidExpression(ast, '"{}" call is not supported yet'.format(ast.node.name))


@visits_expr(nodes.Filter)
def visit_filter(ast, ctx, config):
    return_struct_cls = None
    if ast.name in ('abs', 'striptags', 'capitalize', 'center', 'escape', 'filesizeformat',
                    'float', 'forceescape', 'format', 'indent', 'int', 'replace', 'round',
                    'safe', 'string', 'striptags', 'title', 'trim', 'truncate', 'upper',
                    'urlencode', 'urlize', 'wordcount', 'wordwrap', 'e'):
        ctx.meet(Scalar(), ast)
        if ast.name in ('abs', 'float', 'int', 'round', ):
            node_struct = Number.from_ast(ast.node)
            return_struct_cls = Number
        elif ast.name in ('striptags', 'capitalize', 'center', 'escape', 'forceescape', 'format', 'indent',
                          'replace', 'safe', 'title', 'trim', 'truncate', 'upper', 'urlencode',
                          'urliize', 'wordwrap', 'e'):
            node_struct = String.from_ast(ast.node)
            return_struct_cls = String
        elif ast.name == 'filesizeformat':
            node_struct = Number.from_ast(ast.node)
            return_struct_cls = String
        elif ast.name == 'string':
            node_struct = Scalar.from_ast(ast.node)
            return_struct_cls = String
        elif ast.name == 'wordcount':
            node_struct = String.from_ast(ast.node)
            return_struct_cls = Number
        else:
            node_struct = Scalar.from_ast(ast.node)
    elif ast.name in ('batch', 'slice'):
        ctx.meet(List(List(Unknown())), ast)
        node_struct = merge(
            List(List(Unknown(), linenos=[ast.node.lineno]), linenos=[ast.node.lineno]),
            ctx.get_predicted_struct()
        ).item
    elif ast.name == 'default':
        default_value_rtype, default_value_struct = visit_expr(
            ast.args[0], Context(predicted_struct=Unknown.from_ast(ast.args[0])), config)
        node_struct = merge(
            ctx.get_predicted_struct(),
            default_value_rtype,
        )
        node_struct.used_with_default = True
    elif ast.name == 'dictsort':
        ctx.meet(List(Tuple([Scalar(), Unknown()])), ast)
        node_struct = Dictionary.from_ast(ast.node)
    elif ast.name == 'join':
        ctx.meet(Scalar(), ast)
        node_struct = List.from_ast(ast.node, String())
        rtype, struct = visit_expr(ast.node, Context(
            return_struct_cls=String,
            predicted_struct=node_struct
        ), config)
        arg_rtype, arg_struct = visit_expr(ast.args[0], Context(predicted_struct=Scalar.from_ast(ast.args[0])), config)
        return rtype, merge(struct, arg_struct)
    elif ast.name in ('first', 'last', 'random', 'length', 'sum'):
        if ast.name in ('first', 'last', 'random'):
            el_struct = ctx.get_predicted_struct()
        elif ast.name == 'length':
            ctx.meet(Scalar(), ast)
            el_struct = Unknown()
        else:
            ctx.meet(Scalar(), ast)
            el_struct = Scalar()
        node_struct = List.from_ast(ast.node, el_struct)
    elif ast.name in ('groupby', 'map', 'reject', 'rejectattr', 'select', 'selectattr', 'sort'):
        ctx.meet(List(Unknown()), ast)
        node_struct = merge(
            List(Unknown()),
            ctx.get_predicted_struct()
        )
    elif ast.name == 'list':
        ctx.meet(List(Scalar()), ast)
        node_struct = merge(
            List(Scalar.from_ast(ast.node)),
            ctx.get_predicted_struct()
        ).item
    elif ast.name == 'pprint':
        ctx.meet(Scalar(), ast)
        node_struct = ctx.get_predicted_struct()
    elif ast.name == 'xmlattr':
        ctx.meet(Scalar(), ast)
        node_struct = Dictionary.from_ast(ast.node)
    elif ast.name == 'attr':
        raise InvalidExpression(ast, 'attr filter is not supported')
    else:
        raise InvalidExpression(ast, 'unknown filter')
    rv = visit_expr(ast.node, Context(
        ctx=ctx,
        return_struct_cls=return_struct_cls,
        predicted_struct=node_struct
    ), config)
    return rv


# :class:`nodes.Literal` visitors

@visits_expr(nodes.TemplateData)
def visit_template_data(ast, ctx, config):
    return Scalar(), Dictionary()


@visits_expr(nodes.Const)
def visit_const(ast, ctx, config):
    ctx.meet(Scalar(), ast)
    if isinstance(ast.value, _compat.string_types):
        rtype = String.from_ast(ast, constant=True)
    elif isinstance(ast.value, (int, float, complex)):
        rtype = Number.from_ast(ast, constant=True)
    elif isinstance(ast.value, bool):
        rtype = Boolean.from_ast(ast, constant=True)
    else:
        rtype = Scalar.from_ast(ast, constant=True)
    return rtype, Dictionary()


@visits_expr(nodes.Tuple)
def visit_tuple(ast, ctx, config):
    ctx.meet(Tuple(None), ast)

    struct = Dictionary()
    item_structs = []
    for item in ast.items:
        item_rtype, item_struct = visit_expr(item, ctx, config)
        item_structs.append(item_rtype)
        struct = merge(struct, item_struct)
    rtype = Tuple.from_ast(ast, item_structs, constant=True)
    return rtype, struct


@visits_expr(nodes.List)
def visit_list(ast, ctx, config):
    ctx.meet(List(Unknown()), ast)
    struct = Dictionary()

    predicted_struct = merge(List(Unknown()), ctx.get_predicted_struct()).item
    el_rtype = None
    for item in ast.items:
        item_rtype, item_struct = visit_expr(item, Context(predicted_struct=predicted_struct), config)
        struct = merge(struct, item_struct)
        if el_rtype is None:
            el_rtype = item_rtype
        else:
            el_rtype = merge_rtypes(el_rtype, item_rtype)
    rtype = List.from_ast(ast, el_rtype or Unknown(), constant=True)
    return rtype, struct


@visits_expr(nodes.Dict)
def visit_dict(ast, ctx, config):
    ctx.meet(Dictionary(), ast)
    return _visit_dict(ast, ctx, [(item.key, item.value) for item in ast.items], config)
