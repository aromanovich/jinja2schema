import itertools
from jinja2 import nodes

from ..exceptions import InvalidExpression
from ..mergers import merge
from ..context import Context
from ..model import Scalar, Dictionary, List, Unknown, Tuple
from . import visits_stmt, visit_expr, visit_many


@visits_stmt(nodes.For)
def visit_for(ast):
    body_struct = visit_many(ast.body, Scalar)
    else_struct = visit_many(ast.else_, Scalar)

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
    if_struct = visit_many(ast.body, Scalar)
    else_struct = visit_many(ast.else_, Scalar) if ast.else_ else Dictionary()
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
    return visit_many(ast.nodes, Scalar)


@visits_stmt(nodes.Template)
def visit_template(ast):
    return visit_many(ast.body, Scalar)
