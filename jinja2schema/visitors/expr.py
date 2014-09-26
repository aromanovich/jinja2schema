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
from ..mergers import merge_rtypes, merge, merge_many, merge_bool_expr_structs
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
        def wrapped_func(ast, ctx, macroses, config):
            assert isinstance(ast, node_cls)
            return func(ast, ctx, macroses, config)
        return wrapped_func
    return decorator


def visit_expr(ast, ctx, macroses, config):
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
        raise Exception('expression visitor for {0} is not found'.format(type(ast)))
    return visitor(ast, ctx, macroses, config)


def _visit_dict(ast, ctx, macroses, items, config):
    """A common logic behind nodes.Dict and nodes.Call (``{{ dict(a=1) }}``)
    visitors.

    :param items: a list of (key, value); key may be either AST node or string
    """
    ctx.meet(Dictionary(), ast)
    rtype = Dictionary.from_ast(ast, constant=True)
    struct = Dictionary()
    for key, value in items:
        value_rtype, value_struct = visit_expr(value, Context(
            predicted_struct=Unknown.from_ast(value)), macroses, config)
        struct = merge(struct, value_struct)
        if isinstance(key, nodes.Node):
            key_rtype, key_struct = visit_expr(key, Context(predicted_struct=Scalar.from_ast(key)), macroses, config)
            struct = merge(struct, key_struct)
            if isinstance(key, nodes.Const):
                rtype[key.value] = value_rtype
        elif isinstance(key, _compat.string_types):
            rtype[key] = value_rtype
    return rtype, struct


@visits_expr(nodes.BinExpr)
def visit_bin_expr(ast, ctx, macroses, config):
    l_rtype, l_struct = visit_expr(ast.left, ctx, macroses, config)
    r_rtype, r_struct = visit_expr(ast.right, ctx, macroses, config)
    rv = merge_bool_expr_structs(l_struct, r_struct)
    return merge_rtypes(l_rtype, r_rtype, operator=ast.operator), rv


@visits_expr(nodes.UnaryExpr)
def visit_unary_expr(ast, ctx, macroses, config):
    return visit_expr(ast.node, ctx, macroses, config)


@visits_expr(nodes.Compare)
def visit_compare(ast, ctx, macroses, config):
    ctx.meet(Boolean(), ast)
    rtype, struct = visit_expr(ast.expr, Context(predicted_struct=Unknown.from_ast(ast.expr)),
                               macroses, config)
    for op in ast.ops:
        op_rtype, op_struct = visit_expr(op.expr, Context(predicted_struct=Unknown.from_ast(ast.expr)),
                                         macroses, config)
        struct = merge(struct, op_struct)
    return Boolean.from_ast(ast), struct


@visits_expr(nodes.Slice)
def visit_slice(ast, ctx, macroses, config):
    nodes = [node for node in [ast.start, ast.stop, ast.step] if node is not None]
    struct = visit_many(nodes, macroses, config,
                        predicted_struct_cls=Number,
                        return_struct_cls=Number)
    return Unknown(), struct


@visits_expr(nodes.Name)
def visit_name(ast, ctx, macroses, config):
    kwargs = {}
    return ctx.return_struct_cls.from_ast(ast, **kwargs), Dictionary({
        ast.name: ctx.get_predicted_struct(label=ast.name)
    })


@visits_expr(nodes.Getattr)
def visit_getattr(ast, ctx, macroses, config):
    context = Context(
        ctx=ctx,
        predicted_struct=Dictionary.from_ast(ast, {
            ast.attr: ctx.get_predicted_struct(label=ast.attr),
        }))
    return visit_expr(ast.node, context, macroses, config)


@visits_expr(nodes.Getitem)
def visit_getitem(ast, ctx, macroses, config):
    arg = ast.arg
    if isinstance(arg, nodes.Const):
        if isinstance(arg.value, int):
            if config.TYPE_OF_VARIABLE_INDEXED_WITH_INTEGER_TYPE == 'list':
                predicted_struct = List.from_ast(ast, ctx.get_predicted_struct())
            elif config.TYPE_OF_VARIABLE_INDEXED_WITH_INTEGER_TYPE == 'dictionary':
                predicted_struct = Dictionary.from_ast(ast, {
                    arg.value: ctx.get_predicted_struct(),
                })
            elif config.TYPE_OF_VARIABLE_INDEXED_WITH_INTEGER_TYPE == 'tuple':
                items = [Unknown() for i in range(arg.value + 1)]
                items[arg.value] = ctx.get_predicted_struct()
                predicted_struct = Tuple.from_ast(ast, tuple(items), may_be_extended=True)
        elif isinstance(arg.value, _compat.string_types):
            predicted_struct = Dictionary.from_ast(ast, {
                arg.value: ctx.get_predicted_struct(label=arg.value),
            })
        else:
            raise InvalidExpression(arg, '{0} is not supported as an index for a list or'
                                         ' a key for a dictionary'.format(arg.value))
    elif isinstance(arg, nodes.Slice):
        predicted_struct = List.from_ast(ast, ctx.get_predicted_struct())
    else:
        if config.TYPE_OF_VARIABLE_INDEXED_WITH_VARIABLE_TYPE == 'list':
            predicted_struct = List.from_ast(ast, ctx.get_predicted_struct())
        elif config.TYPE_OF_VARIABLE_INDEXED_WITH_VARIABLE_TYPE == 'dictionary':
            predicted_struct = Dictionary.from_ast(ast)

    _, arg_struct = visit_expr(arg, Context(predicted_struct=Scalar.from_ast(arg)), macroses, config)
    rtype, struct = visit_expr(ast.node, Context(
        ctx=ctx,
        predicted_struct=predicted_struct), macroses, config)
    return rtype, merge(struct, arg_struct)


@visits_expr(nodes.Test)
def visit_test(ast, ctx, macroses, config):
    ctx.meet(Boolean(), ast)
    if ast.name in ('divisibleby', 'escaped', 'even', 'lower', 'odd', 'upper'):
        # TODO
        predicted_struct = Scalar.from_ast(ast.node)
    elif ast.name in ('defined', 'undefined', 'equalto', 'iterable', 'mapping',
                      'none', 'number', 'sameas', 'sequence', 'string'):
        predicted_struct = Unknown.from_ast(ast.node)
        if ast.name == 'defined':
            predicted_struct.checked_as_defined = True
        elif ast.name == 'undefined':
            predicted_struct.checked_as_undefined = True
    else:
        raise InvalidExpression(ast, 'unknown test "{0}"'.format(ast.name))
    rtype, struct = visit_expr(ast.node, Context(return_struct_cls=Boolean,
                                                 predicted_struct=predicted_struct), macroses, config)
    if ast.name == 'divisibleby':
        if not ast.args:
            raise InvalidExpression(ast, 'divisibleby must have an argument')
        _, arg_struct = visit_expr(ast.args[0],
                                   Context(predicted_struct=Number.from_ast(ast.args[0])), macroses, config)
        struct = merge(arg_struct, struct)
    return rtype, struct


@visits_expr(nodes.Concat)
def visit_concat(ast, ctx, macroses, config):
    ctx.meet(Scalar(), ast)
    return String.from_ast(ast), visit_many(ast.nodes, macroses, config, predicted_struct_cls=String)


@visits_expr(nodes.CondExpr)
def visit_cond_expr(ast, ctx, macroses, config):
    if config.CONSIDER_CONDITIONS_AS_BOOLEAN:
        test_predicted_struct = Boolean.from_ast(ast.test)
    else:
        test_predicted_struct = Unknown.from_ast(ast.test)
    test_rtype, test_struct = visit_expr(ast.test, Context(predicted_struct=test_predicted_struct), macroses, config)
    if_rtype, if_struct = visit_expr(ast.expr1, ctx, macroses, config)
    else_rtype, else_struct = visit_expr(ast.expr2, ctx, macroses, config)
    struct = merge_many(if_struct, test_struct, else_struct)
    rtype = merge_rtypes(if_rtype, else_rtype)

    for var_name, var_struct in test_struct.iteritems():
        if var_struct.checked_as_defined or var_struct.checked_as_undefined:
            if var_struct.checked_as_undefined:
                lookup_struct = if_struct
            elif var_struct.checked_as_defined:
                lookup_struct = else_struct
            struct[var_name].may_be_defined = (lookup_struct and
                                               var_name in lookup_struct and
                                               lookup_struct[var_name].assigned)
        struct[var_name].checked_as_defined = test_struct[var_name].checked_as_defined
        struct[var_name].checked_as_undefined = test_struct[var_name].checked_as_undefined

    return rtype, struct


def check_macro_call(ast, macro, args, kwargs):
    # XXX the code needs to be refactored
    rv = Dictionary()

    expected_args = macro.args[:]
    expected_kwargs = macro.kwargs[:]

    def match_args(args, expected_args):
        matched_args = list(zip(args, expected_args))
        for i, (arg, (expected_arg_name, expected_arg)) in enumerate(matched_args, start=1):
            old_label = arg.label
            arg.label = 'argument #{0}'.format(i)
            arg_struct = merge(expected_arg, arg)
            if old_label:
                arg_struct.label = old_label
                rv[old_label] = arg_struct

        args = args[len(matched_args):]
        expected_args = expected_args[len(matched_args):]
        return args, expected_args

    args, expected_args = match_args(args, expected_args)

    if args:
        args, expected_kwargs = match_args(args, expected_kwargs)


    def match_kwarg(kwarg_name, kwarg, expected_kwargs):
        r = []
        found = False
        for (expected_kwarg_name, expected_kwarg) in expected_kwargs:
            if kwarg_name == expected_kwarg_name:
                kwarg_struct = merge(expected_kwarg, kwarg)  # to make sure
                if kwarg.label:
                    kwarg_struct.label = kwarg.label
                    rv[kwarg.label] = kwarg_struct
                found = True
            else:
                r.append((expected_kwarg_name, expected_kwarg))
        return r, found

    for kwarg, kwarg_type in _compat.iteritems(kwargs):
        expected_args, found_1 = match_kwarg(kwarg, kwarg_type, expected_args)
        expected_kwargs, found_2 = match_kwarg(kwarg, kwarg_type, expected_kwargs)
        if not (found_1 or found_2):
            raise InvalidExpression(ast, 'incorrect usage of "{0}". unknown argument "{1}"'.format(macro.name, kwarg))


    if args or expected_args:
        raise InvalidExpression(ast, ('incorrect usage of "{0}". it takes '
                                      'exactly {1} positional arguments'.format(macro.name, len(macro.args))))

    return rv


@visits_expr(nodes.Call)
def visit_call(ast, ctx, macroses, config):
    if isinstance(ast.node, nodes.Name):
        if ast.node.name in macroses:
            # XXX the code needs to be refactored
            struct = Dictionary()
            macro = macroses[ast.node.name]

            arg_structures = []
            for arg_ast in ast.args:
                arg_rtype, arg_struct = visit_expr(
                    arg_ast, Context(predicted_struct=Unknown.from_ast(arg_ast)), macroses, config)
                struct = merge(struct, arg_struct)
                arg_structures.append(arg_rtype)

            kwarg_structures = {}
            for kwarg_ast in ast.kwargs:
                kwarg_rtype, kwarg_struct = visit_expr(
                    kwarg_ast.value, Context(predicted_struct=Unknown.from_ast(kwarg_ast)), macroses, config)
                struct = merge(struct, kwarg_struct)
                kwarg_structures[kwarg_ast.key] = kwarg_rtype

            args_struct = check_macro_call(ast, macro, arg_structures, kwarg_structures)

            return Unknown(), merge(args_struct, struct)
        elif ast.node.name == 'range':
            ctx.meet(List(Unknown()), ast)
            struct = Dictionary()
            for arg in ast.args:
                arg_rtype, arg_struct = visit_expr(arg, Context(
                    predicted_struct=Number.from_ast(arg)), macroses, config)
                struct = merge(struct, arg_struct)
            return List(Number()), struct
        elif ast.node.name == 'lipsum':
            ctx.meet(Scalar(), ast)
            struct = Dictionary()
            # perhaps TODO: set possible types for args and kwargs
            for arg in ast.args:
                arg_rtype, arg_struct = visit_expr(arg, Context(predicted_struct=Scalar.from_ast(arg)), macroses, config)
                struct = merge(struct, arg_struct)
            for kwarg in ast.kwargs:
                arg_rtype, arg_struct = visit_expr(kwarg.value, Context(predicted_struct=Scalar.from_ast(kwarg)), macroses, config)
                struct = merge(struct, arg_struct)
            return Scalar(), struct
        elif ast.node.name == 'dict':
            ctx.meet(Dictionary(), ast)
            if ast.args:
                raise InvalidExpression(ast, 'dict accepts only keyword arguments')
            return _visit_dict(ast, ctx, macroses, [(kwarg.key, kwarg.value) for kwarg in ast.kwargs], config)
        else:
            raise InvalidExpression(ast, '"{0}" call is not supported yet'.format(ast.node.name))
    elif isinstance(ast.node, nodes.Getattr):
        if ast.node.attr in ('keys', 'iterkeys', 'values', 'itervalues'):
            ctx.meet(List(Unknown()), ast)
            rtype, struct = visit_expr(
                ast.node.node, Context(predicted_struct=Dictionary.from_ast(ast.node.node)), macroses, config)
            return List(Unknown()), struct



@visits_expr(nodes.Filter)
def visit_filter(ast, ctx, macroses, config):
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
            ast.args[0], Context(predicted_struct=Unknown.from_ast(ast.args[0])), macroses, config)
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
        ), macroses, config)
        arg_rtype, arg_struct = visit_expr(ast.args[0], Context(predicted_struct=Scalar.from_ast(ast.args[0])), macroses, config)
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
    ), macroses, config)
    return rv


# :class:`nodes.Literal` visitors

@visits_expr(nodes.TemplateData)
def visit_template_data(ast, ctx, macroses, config):
    return Scalar(), Dictionary()


@visits_expr(nodes.Const)
def visit_const(ast, ctx, macroses, config):
    ctx.meet(Scalar(), ast)
    if isinstance(ast.value, _compat.string_types):
        rtype = String.from_ast(ast, constant=True)
    elif isinstance(ast.value, bool):
        rtype = Boolean.from_ast(ast, constant=True)
    elif isinstance(ast.value, (int, float, complex)):
        rtype = Number.from_ast(ast, constant=True)
    else:
        rtype = Scalar.from_ast(ast, constant=True)
    return rtype, Dictionary()


@visits_expr(nodes.Tuple)
def visit_tuple(ast, ctx, macroses, config):
    ctx.meet(Tuple(None), ast)

    struct = Dictionary()
    item_structs = []
    for item in ast.items:
        item_rtype, item_struct = visit_expr(item, ctx, macroses, config)
        item_structs.append(item_rtype)
        struct = merge(struct, item_struct)
    rtype = Tuple.from_ast(ast, item_structs, constant=True)
    return rtype, struct


@visits_expr(nodes.List)
def visit_list(ast, ctx, macroses, config):
    ctx.meet(List(Unknown()), ast)
    struct = Dictionary()

    predicted_struct = merge(List(Unknown()), ctx.get_predicted_struct()).item
    el_rtype = None
    for item in ast.items:
        item_rtype, item_struct = visit_expr(item, Context(predicted_struct=predicted_struct), macroses, config)
        struct = merge(struct, item_struct)
        if el_rtype is None:
            el_rtype = item_rtype
        else:
            el_rtype = merge_rtypes(el_rtype, item_rtype)
    rtype = List.from_ast(ast, el_rtype or Unknown(), constant=True)
    return rtype, struct


@visits_expr(nodes.Dict)
def visit_dict(ast, ctx, macroses, config):
    ctx.meet(Dictionary(), ast)
    return _visit_dict(ast, ctx, macroses, [(item.key, item.value) for item in ast.items], config)
