import pytest
from jinja2 import nodes

from jinja2schema import parse, UnexpectedExpression, InvalidExpression
from jinja2schema.visitors.expr import visit_filter, Context
from jinja2schema.model import Dictionary, Scalar, List, Unknown, String, Number


def get_scalar_context(ast):
    return Context(return_struct_cls=Scalar, predicted_struct=Scalar.from_ast(ast))


def test_string_filters():
    for filter in ('striptags', 'capitalize', 'title', 'upper', 'urlize'):
        template = '{{ x|' + filter + ' }}'
        ast = parse(template).find(nodes.Filter)

        ctx = Context(return_struct_cls=Scalar, predicted_struct=Scalar.from_ast(ast))
        rtype, struct = visit_filter(ast, ctx)

        expected_rtype = String(label='x', linenos=[1])
        expected_struct = Dictionary({
            'x': String(label='x', linenos=[1]),
        })
        assert rtype == expected_rtype
        assert struct == expected_struct


def test_batch_and_slice_filters():
    for filter in ('batch', 'slice'):
        template = '{{ items|' + filter + '(3, "&nbsp;") }}'
        ast = parse(template).find(nodes.Filter)

        unknown_ctx = Context(predicted_struct=Unknown.from_ast(ast))
        rtype, struct = visit_filter(ast, unknown_ctx)

        expected_rtype = List(List(Unknown(), linenos=[1]), linenos=[1])
        assert rtype == expected_rtype

        expected_struct = Dictionary({
            'items': List(Unknown(), label='items', linenos=[1]),
        })
        assert struct == expected_struct

        scalar_ctx = Context(predicted_struct=Scalar.from_ast(ast))
        with pytest.raises(UnexpectedExpression) as e:
            visit_filter(ast, scalar_ctx)
        assert str(e.value) == ('conflict on the line 1\n'
                                'got: AST node jinja2.nodes.Filter of structure [[<unknown>]]\n'
                                'expected structure: <scalar>')


def test_default_filter():
    template = '''{{ x|default('g') }}'''
    ast = parse(template).find(nodes.Filter)
    rtype, struct = visit_filter(ast, get_scalar_context(ast))

    expected_struct = Dictionary({
        'x': String(label='x', linenos=[1], used_with_default=True, value='g'),
    })
    assert struct == expected_struct


def test_filter_chaining():
    template = '''{{ (xs|first|last).gsom|sort|length }}'''
    ast = parse(template).find(nodes.Filter)
    rtype, struct = visit_filter(ast, get_scalar_context(ast))

    expected_struct = Dictionary({
        'xs': List(List(Dictionary({
            'gsom': List(Unknown(), label='gsom', linenos=[1]),
        }, linenos=[1]), linenos=[1]), label='xs', linenos=[1]),
    })
    assert struct == expected_struct

    template = '''{{ x|list|sort|first }}'''
    ast = parse(template).find(nodes.Filter)
    rtype, struct = visit_filter(ast, get_scalar_context(ast))

    expected_struct = Dictionary({
        'x': Scalar(label='x', linenos=[1]),
    })
    assert struct == expected_struct

    template = '''{{ x|first|list }}'''
    ast = parse(template).find(nodes.Filter)
    with pytest.raises(UnexpectedExpression):
        visit_filter(ast, get_scalar_context(ast))


def test_raise_on_unknown_filter():
    template = '''{{ x|unknownfilter }}'''
    ast = parse(template).find(nodes.Filter)
    with pytest.raises(InvalidExpression) as e:
        visit_filter(ast, get_scalar_context(ast))
    assert 'unknown filter' in str(e.value)

    template = '''{{ x|attr('attr') }}'''
    ast = parse(template).find(nodes.Filter)
    with pytest.raises(InvalidExpression) as e:
        visit_filter(ast, get_scalar_context(ast))
    assert 'filter is not supported' in str(e.value)


def test_abs_filter():
    ast = parse('{{ x|abs }}').find(nodes.Filter)
    rtype, struct = visit_filter(ast, get_scalar_context(ast))
    assert rtype == Number(label='x', linenos=[1])
    assert struct == Dictionary({
        'x': Number(label='x', linenos=[1])
    })


def test_int_filter():
    ast = parse('{{ x|int }}').find(nodes.Filter)
    rtype, struct = visit_filter(ast, get_scalar_context(ast))
    assert rtype == Number(label='x', linenos=[1])
    assert struct == Dictionary({
        'x': Scalar(label='x', linenos=[1]),
    })


def test_wordcount_filter():
    ast = parse('{{ x|wordcount }}').find(nodes.Filter)
    rtype, struct = visit_filter(ast, get_scalar_context(ast))
    assert rtype == Number(label='x', linenos=[1])
    assert struct == Dictionary({
        'x': String(label='x', linenos=[1])
    })


def test_join_filter():
    ast = parse('{{ xs|join(separator|default("|")) }}').find(nodes.Filter)
    rtype, struct = visit_filter(ast, get_scalar_context(ast))
    assert rtype == String(label='xs', linenos=[1])
    assert struct == Dictionary({
        'xs': List(String(), label='xs', linenos=[1]),
        'separator': String(label='separator', linenos=[1], used_with_default=True, value='|'),
    })


def test_length_filter():
    ast = parse('{{ xs|length }}').find(nodes.Filter)
    rtype, struct = visit_filter(ast, get_scalar_context(ast))
    assert rtype == Number(label='xs', linenos=[1])
    assert struct == Dictionary({
        'xs': List(Unknown(), label='xs', linenos=[1]),
    })