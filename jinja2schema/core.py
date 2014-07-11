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

from .model import Variable, Scalar, Dictionary, List, Unknown, Tuple


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

    :func:`visit_name` does not do much by itself. Based on a context in knows what structure and
    what type must have a variable described by a given :class:`nodes.Name` node, so
    it just returns a pair::

        (instance of context.return_struct_cls, Dictionary({data: context.predicted_struct}})
    """
    def __init__(self, return_struct_cls=None, predicted_struct=None):
        self.return_struct_cls = return_struct_cls if return_struct_cls is not None else Unknown
        self.predicted_struct = predicted_struct if predicted_struct is not None else Unknown()

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


class MergeException(Exception):
    """Conflict of merging two structures.

    .. attribute:: fst

        :class:`Variable`

    .. attribute:: snd

        :class:`Variable`
    """
    def __init__(self, fst, snd):
        self.fst = fst
        self.snd = snd

    def __str__(self):
        get_label = lambda s: 'unnamed variable' if s.label is None else 'variable "{}"'.format(s.label)
        get_usage = lambda s: s.__class__.__name__.lower()
        get_linenos = lambda s: ','.join(map(str, s.linenos))
        return ('{fst_label} (lines: {fst_linenos}, used as {fst_usage}) conflicts with '
                '{snd_label} (lines: {snd_linenos}, used as {snd_usage})').format(
                    fst_label=get_label(self.fst), snd_label=get_label(self.snd),
                    fst_usage=get_usage(self.fst), snd_usage=get_usage(self.snd),
                    fst_linenos=get_linenos(self.fst), snd_linenos=get_linenos(self.snd))


class UnexpectedExpression(Exception):
    """Raised when a visitor was expecting compatibility with :attr:`expected_struct`,
    but got :attr:`actual_ast` of structure :attr:`actual_struct`.

    Compatibility is checked by merging expected structure with actual one.

    .. attribute:: expected_struct

        expected :class:`.model.Variable`

    .. attribute:: actual_ast

        actual :class:`jinja2.nodes.Node`

    .. attribute:: actual_ast

        :class:`.model.Variable` described by ``actual_ast``
    """
    def __init__(self, expected_struct, actual_ast, actual_struct):
        self.expected_struct = expected_struct
        self.actual_ast = actual_ast
        self.actual_struct = actual_struct

    def __str__(self):
        return ('conflict on the line {lineno}\n'
                'got: AST node jinja2.nodes.{node} of structure {actual_struct}\n'
                'expected structure: {expected_struct}').format(
                    lineno=self.actual_ast.lineno,
                    node=self.actual_ast.__class__.__name__,
                    actual_struct=self.actual_struct,
                    expected_struct=self.expected_struct)


class InvalidExpression(Exception):
    """Raised when a template uses Jinja2 features that are not supported by the library
    or when a template contains incorrect expressions (i.e., such as applying ``divisibleby`` filter
    without an argument).

    .. attribute:: ast

        :class:`jinja2.nodes.Node` caused the exception
    """
    def __init__(self, ast, message):
        self.ast = ast
        self.message = message

    def __str__(self):
        return 'line {}: {}'.format(self.ast.lineno, self.message)


def merge(fst, snd):
    """Merges two variables.

    :param fst: first variable
    :type fst: :class:`.model.Variable`
    :param snd: second variable
    :type snd: :class:`.model.Variable`

    .. note::

        ``fst`` must reflect expressions that occur in template **before** the expressions of ``snd``.
    """
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
        result = List(merge(fst.item, snd.item))
    elif isinstance(fst, Tuple) and isinstance(snd, Tuple):
        if fst.items is snd.items is None:
            result = Tuple(None)
        else:
            if len(fst.items) != len(snd.items):
                raise MergeException(fst, snd)
            result = Tuple([merge(a, b) for a, b in zip(fst.items, snd.items)])
    else:
        raise MergeException(fst, snd)
    result.label = fst.label or snd.label
    result.linenos = list(sorted(set(fst.linenos + snd.linenos)))
    result.constant = fst.constant
    result.may_be_defined = fst.may_be_defined
    result.used_with_default = fst.used_with_default and snd.used_with_default
    return result


def merge_rtypes(fst, snd, operator=None):
    if operator in ('+', '-'):
        if type(fst) is not type(snd) and not (isinstance(fst, Unknown) or isinstance(snd, Unknown)):
            raise MergeException(fst, snd)
    return merge(fst, snd)


stmt_visitors = {}
expr_visitors = {}


def visits_stmt(node_cls):
    def decorator(func):
        stmt_visitors[node_cls] = func
        @functools.wraps(func)
        def wrapped_func(ast):
            assert isinstance(ast, node_cls)
            return func(ast)
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
    return Unknown(), visit_nodes_and_merge(nodes, Scalar)


@visits_expr(nodes.Name)
def visit_name(ast, ctx):
    return ctx.return_struct_cls.from_ast(ast), Dictionary({
        ast.name: ctx.get_predicted_struct(label=ast.name)
    })


@visits_expr(nodes.Getattr)
def visit_getattr(ast, ctx):
    context = Context(
        return_struct_cls=ctx.return_struct_cls,
        predicted_struct=Dictionary.from_ast(ast, {
            ast.attr: ctx.get_predicted_struct(label=ast.attr),
        }))
    return visit_expr(ast.node, context)


@visits_expr(nodes.Getitem)
def visit_getitem(ast, ctx):
    arg = ast.arg
    if isinstance(arg, nodes.Const):
        if isinstance(arg.value, int):
            predicted_struct = List.from_ast(arg, ctx.get_predicted_struct())
        elif isinstance(arg.value, basestring):
            predicted_struct = Dictionary.from_ast(arg, {
                arg.value: ctx.get_predicted_struct(label=arg.value),
            })
        else:
            raise InvalidExpression(arg, '{} is not supported as an index for a list or'
                                         ' a key for a dictionary'.format(arg.value))
    else:
        predicted_struct = List.from_ast(arg, ctx.get_predicted_struct())

    _, arg_struct = visit_expr(arg, Context(predicted_struct=Scalar.from_ast(arg)))
    rtype, struct = visit_expr(ast.node, Context(
        return_struct_cls=ctx.return_struct_cls,
        predicted_struct=predicted_struct))
    return rtype, merge(struct, arg_struct)


@visits_expr(nodes.Test)
def visit_test(ast, ctx):
    if ast.name in ('divisibleby', 'escaped', 'even', 'lower', 'odd', 'upper'):
        ctx.meet(Scalar(), ast)
        predicted_struct = Scalar.from_ast(ast.node)
    elif ast.name in ('defined', 'undefined', 'equalto', 'iterable', 'mapping',
                      'none', 'number', 'sameas', 'sequence', 'string'):
        predicted_struct = Unknown.from_ast(ast.node)
    else:
        raise InvalidExpression(ast, 'unknown test "{}"'.format(ast.name))
    rtype, struct = visit_expr(ast.node, Context(return_struct_cls=Scalar, predicted_struct=predicted_struct))
    if ast.name == 'divisibleby':
        if not ast.args:
            raise InvalidExpression(ast, 'divisibleby must have an argument')
        _, arg_struct = visit_expr(ast.args[0],
                                   Context(predicted_struct=Scalar.from_ast(ast.args[0])))
        struct = merge(arg_struct, struct)
    return rtype, struct


@visits_expr(nodes.Concat)
def visit_concat(ast, ctx):
    ctx.meet(Scalar(), ast)
    return Scalar.from_ast(ast), visit_nodes_and_merge(ast.nodes, Scalar)


@visits_expr(nodes.CondExpr)
def visit_cond_expr(ast, ctx):
    test_rtype, test_struct = visit_expr(ast.test, Context(predicted_struct=Unknown.from_ast(ast.test)))
    if_rtype, if_struct = visit_expr(ast.expr1, ctx)
    else_rtype, else_struct = visit_expr(ast.expr2, ctx)
    struct = merge(merge(if_struct, test_struct), else_struct)
    rtype = merge_rtypes(if_rtype, else_rtype)

    if (isinstance(ast.test, nodes.Test) and isinstance(ast.test.node, nodes.Name) and
            ast.test.name in ('defined', 'undefined')):
        struct[ast.test.node.name].may_be_defined = True
    return rtype, struct


@visits_expr(nodes.Call)
def visit_call(ast, ctx):
    if isinstance(ast.node, nodes.Name):
        if ast.node.name == 'range':
            ctx.meet(List(Unknown()), ast)
            struct = Dictionary()
            for arg in ast.args:
                arg_rtype, arg_struct = visit_expr(arg, Context(predicted_struct=Scalar.from_ast(arg)))
                struct = merge(struct, arg_struct)
            return List(Scalar()), struct
        elif ast.node.name == 'lipsum':
            ctx.meet(Scalar(), ast)
            struct = Dictionary()
            for arg in ast.args:
                arg_rtype, arg_struct = visit_expr(arg, Context(predicted_struct=Scalar.from_ast(arg)))
                struct = merge(struct, arg_struct)
            for kwarg in ast.kwargs:
                arg_rtype, arg_struct = visit_expr(kwarg.value, Context(predicted_struct=Scalar.from_ast(kwarg)))
                struct = merge(struct, arg_struct)
            return Scalar(), struct
        elif ast.node.name == 'dict':
            ctx.meet(Dictionary(), ast)
            if ast.args:
                raise InvalidExpression(ast, 'dict accepts only keyword arguments')
            return _visit_dict(ast, ctx, [(kwarg.key, kwarg.value) for kwarg in ast.kwargs])
        else:
            raise InvalidExpression(ast, '"{}" call is not supported yet'.format(ast.node.name))


@visits_expr(nodes.Filter)
def visit_filter(ast, ctx):
    if ast.name in ('abs', 'striptags', 'capitalize', 'center', 'escape', 'filesizeformat',
                    'float', 'forceescape', 'format', 'indent', 'int', 'replace', 'round',
                    'safe', 'string', 'striptags', 'title', 'trim', 'truncate', 'upper',
                    'urlencode', 'urlize', 'wordcount', 'wordwrap', 'e'):
        ctx.meet(Scalar(), ast)
        node_struct = Scalar.from_ast(ast.node)
    elif ast.name in ('batch', 'slice'):
        ctx.meet(List(List(Unknown())), ast)
        node_struct = merge(
            List(List(Unknown(), linenos=[ast.node.lineno]), linenos=[ast.node.lineno]),
            ctx.get_predicted_struct()
        ).item
    elif ast.name == 'default':
        default_value_rtype, default_value_struct = visit_expr(
            ast.args[0], Context(predicted_struct=Unknown.from_ast(ast.args[0])))
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
        node_struct = List.from_ast(ast.node, Scalar())
        rtype, struct = visit_expr(ast.node, Context(
            return_struct_cls=ctx.return_struct_cls,
            predicted_struct=node_struct
        ))
        arg_rtype, arg_struct = visit_expr(ast.args[0], Context(predicted_struct=Scalar.from_ast(ast.args[0])))
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

    return visit_expr(ast.node, Context(
        return_struct_cls=ctx.return_struct_cls,
        predicted_struct=node_struct
    ))


# :class:`nodes.Literal` visitors

@visits_expr(nodes.TemplateData)
def visit_template_data(ast, ctx):
    return Scalar(), Dictionary()


@visits_expr(nodes.Const)
def visit_const(ast, ctx):
    ctx.meet(Scalar(), ast)
    return Scalar.from_ast(ast, constant=True), Dictionary()


@visits_expr(nodes.Tuple)
def visit_tuple(ast, ctx):
    ctx.meet(Tuple(None), ast)

    struct = Dictionary()
    item_structs = []
    for item in ast.items:
        item_rtype, item_struct = visit_expr(item, ctx)
        item_structs.append(item_rtype)
        struct = merge(struct, item_struct)
    rtype = Tuple.from_ast(ast, item_structs, constant=True)
    return rtype, struct


@visits_expr(nodes.List)
def visit_list(ast, ctx):
    ctx.meet(List(Unknown()), ast)
    struct = Dictionary()

    predicted_struct = merge(List(Unknown()), ctx.get_predicted_struct()).item
    el_rtype = None
    for item in ast.items:
        item_rtype, item_struct = visit_expr(item, Context(predicted_struct=predicted_struct))
        struct = merge(struct, item_struct)
        if el_rtype is None:
            el_rtype = item_rtype
        else:
            el_rtype = merge_rtypes(el_rtype, item_rtype)
    rtype = List.from_ast(ast, el_rtype or Unknown(), constant=True)
    return rtype, struct


def _visit_dict(ast, ctx, items):
    """A common logic behind nodes.Dict and nodes.Call (``{{ dict(a=1) }}``)
    visitors.

    :param items: a list of (key, value); key may be either ast or string
    """
    ctx.meet(Dictionary(), ast)
    rtype = Dictionary.from_ast(ast, constant=True)
    struct = Dictionary()
    for key, value in items:
        value_rtype, value_struct = visit_expr(value, Context(
            predicted_struct=Unknown.from_ast(value)))
        struct = merge(struct, value_struct)
        if isinstance(key, nodes.Node):
            key_rtype, key_struct = visit_expr(key, Context(predicted_struct=Scalar.from_ast(key)))
            struct = merge(struct, key_struct)
            if isinstance(key, nodes.Const):
                rtype[key.value] = value_rtype
        elif isinstance(key, basestring):
            rtype[key] = value_rtype
    return rtype, struct


@visits_expr(nodes.Dict)
def visit_dict(ast, ctx):
    ctx.meet(Dictionary(), ast)
    return _visit_dict(ast, ctx, [(item.key, item.value) for item in ast.items])


# Statement visitors

@visits_stmt(nodes.For)
def visit_for(ast):
    body_struct = visit_nodes_and_merge(ast.body, Scalar)
    else_struct = visit_nodes_and_merge(ast.else_, Scalar)

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
            predicted_struct=List.from_ast(ast, target_struct)))

    merge(iter_rtype, List(target_struct))

    return merge(merge(iter_struct, body_struct), else_struct)


@visits_stmt(nodes.If)
def visit_if(ast):
    test_rtype, test_struct = visit_expr(ast.test, Context(
        return_struct_cls=Unknown,
        predicted_struct=Unknown.from_ast(ast.test)))
    if_struct = visit_nodes_and_merge(ast.body, Scalar)
    else_struct = visit_nodes_and_merge(ast.else_, Scalar) if ast.else_ else Dictionary()
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
def visit_assign(ast):
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
            for name_ast, var_ast in itertools.izip(ast.target.items, ast.node.items):
                variables.append((name_ast.name, var_ast))
        for var_name, var_ast in variables:
            var_rtype, var_struct = visit_expr(var_ast, Context(predicted_struct=Unknown.from_ast(var_ast)))
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
            ast.node, Context(return_struct_cls=Unknown, predicted_struct=Tuple(tuple_items)))
        return merge(struct, var_struct)
    else:
        raise InvalidExpression(ast, 'unsupported assignment')


@visits_stmt(nodes.Output)
def visit_output(ast):
    return visit_nodes_and_merge(ast.nodes, Scalar)


@visits_stmt(nodes.Template)
def visit_template(ast):
    return visit_nodes_and_merge(ast.body, Scalar)


def visit_nodes_and_merge(nodes, predicted_struct_class):
    rv = Dictionary()
    for node in nodes:
        rv = merge(rv, visit(node, Context(
            return_struct_cls=Scalar,
            predicted_struct=predicted_struct_class.from_ast(node))))
    return rv


def visit_stmt(ast):
    visitor = stmt_visitors.get(type(ast))
    if not visitor:
        for node_cls, visitor_ in stmt_visitors.iteritems():
            if isinstance(ast, node_cls):
                visitor = visitor_
    if not visitor:
        raise Exception('stmt visitor for {} is not found'.format(type(ast)))
    return visitor(ast)


def visit_expr(ast, ctx):
    visitor = expr_visitors.get(type(ast))
    if not visitor:
        for node_cls, visitor_ in expr_visitors.iteritems():
            if isinstance(ast, node_cls):
                visitor = visitor_
    if not visitor:
        raise Exception('expr visitor for {} is not found'.format(type(ast)))
    return visitor(ast, ctx)


def visit(ast, ctx):
    if isinstance(ast, nodes.Stmt):
        structure = visit_stmt(ast)
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


def infer_from_ast(ast):
    """
    :type ast: :class:`nodes.Template`
    """
    rv = visit_nodes_and_merge(ast.body, Scalar)
    return _post_process(rv)


def parse(template, jinja2_env=None):
    """
    :type template: basestring
    :type jinja2_env: :class:`jinja2.Environment`
    :rtype: :class:`nodes.Template`
    """
    if jinja2_env is None:
        jinja2_env = jinja2.Environment()
    return jinja2_env.parse(template)


def infer(template):
    """Returns a :class:`Dictionary` that describes a structure of a context required by ``template``.

    :type template: basestring
    :rtype: class:`Dictionary`
    """
    return infer_from_ast(parse(template))
