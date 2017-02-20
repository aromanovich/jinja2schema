# coding: utf-8
import pytest
from jinja2 import nodes

from jinja2schema.core import parse
from jinja2schema.exceptions import InvalidExpression
from jinja2schema.model import List, Dictionary, Scalar, Unknown, String, Boolean, Number
from jinja2schema.visitors.expr import visit_call, Context


def get_scalar_context(ast):
    return Context(return_struct_cls=Scalar, predicted_struct=Scalar.from_ast(ast))


def test_range_call():
    template = '{{ range(n) }}'
    ast = parse(template).find(nodes.Call)

    rtype, struct = visit_call(ast, Context(predicted_struct=Unknown()))

    expected_rtype = List(Number())
    assert rtype == expected_rtype

    expected_struct = Dictionary({
        'n': Number(label='n', linenos=[1]),
    })
    assert struct == expected_struct


def test_lipsum_call():
    template = '{{ lipsum(n) }}'
    ast = parse(template).find(nodes.Call)

    rtype, struct = visit_call(ast, Context(predicted_struct=Unknown()))

    expected_rtype = String()
    assert rtype == expected_rtype

    expected_struct = Dictionary({
        'n': Scalar(label='n', linenos=[1]),  # TODO must be Number
    })
    assert struct == expected_struct


def test_dict_call():
    template = '''{{ dict(x=\ndict(\na=1, b=2), y=a) }}'''
    call_ast = parse(template).find(nodes.Call)
    rtype, struct = visit_call(
        call_ast, Context(predicted_struct=Unknown.from_ast(call_ast)))

    expected_rtype = Dictionary({
        'x': Dictionary({
            'a': Number(linenos=[3], constant=True, value=1),
            'b': Number(linenos=[3], constant=True, value=2)
        }, linenos=[2], constant=True),
        'y': Unknown(label='a', linenos=[3]),
    }, linenos=[1], constant=True)
    assert rtype == expected_rtype

    expected_struct = Dictionary({
        'a': Unknown(label='a', linenos=[3]),
    })
    assert struct == expected_struct


def test_str_method_calls():
    template = '''{{ x.endswith(suffix) }}'''
    call_ast = parse(template).find(nodes.Call)
    rtype, struct = visit_call(call_ast, get_scalar_context(call_ast))

    expected_rtype = Boolean()
    assert rtype == expected_rtype

    expected_struct = Dictionary({
        'x': String(label='x', linenos=[1]),
        # TODO suffix must be in struct too
    })
    assert struct == expected_struct

    template = '''{{ x.split(separator) }}'''
    call_ast = parse(template).find(nodes.Call)
    ctx = Context(return_struct_cls=Unknown, predicted_struct=Unknown.from_ast(call_ast))
    rtype, struct = visit_call(call_ast, ctx)

    expected_rtype = List(String())
    assert rtype == expected_rtype

    expected_struct = Dictionary({
        'x': String(label='x', linenos=[1]),
        'separator': String(label='separator', linenos=[1]),
    })
    assert struct == expected_struct



def test_raise_on_unknown_call():
    for template in ('{{ x.some_unknown_f() }}', '{{ xxx() }}'):
        call_ast = parse(template).find(nodes.Call)
        with pytest.raises(InvalidExpression) as e:
            visit_call(call_ast, get_scalar_context(call_ast))
        assert 'call is not supported' in str(e.value)
