from jinja2 import nodes
import pytest
from jinja2schema import parse, Config, UnexpectedExpression, InvalidExpression
from jinja2schema.visitors.expr import visit_filter, Context
from jinja2schema.model import Dictionary, Scalar, List, Unknown, String, Number, Boolean, Tuple


test_config = Config()


def get_context(ast):
    return Context(return_struct_cls=Scalar, predicted_struct=Scalar.from_ast(ast))


def test_filter_1():
    template = '{{ x|striptags }}'
    ast = parse(template).find(nodes.Filter)
    rtype, struct = visit_filter(ast, get_context(ast), {}, test_config)

    expected_struct = Dictionary({
        'x': String(label='x', linenos=[1]),
    })
    assert struct == expected_struct


def test_filter_2():
    template = '''{{ items|batch(3, '&nbsp;') }}'''
    ast = parse(template).find(nodes.Filter)
    with pytest.raises(UnexpectedExpression):
        visit_filter(ast, get_context(ast), {}, test_config)


def test_filter_3():
    template = '''{{ x|default('g') }}'''
    ast = parse(template).find(nodes.Filter)
    rtype, struct = visit_filter(ast, get_context(ast), {}, test_config)

    expected_struct = Dictionary({
        'x': String(label='x', linenos=[1], used_with_default=True),
    })
    assert struct == expected_struct


def test_filter_4():
    template = '''{{ (xs|first|last).gsom|sort|length }}'''
    ast = parse(template).find(nodes.Filter)
    rtype, struct = visit_filter(ast, get_context(ast), {}, test_config)

    expected_struct = Dictionary({
        'xs': List(List(Dictionary({
            'gsom': List(Unknown(), label='gsom', linenos=[1]),
        }, linenos=[1]), linenos=[1]), label='xs', linenos=[1]),
    })
    assert struct == expected_struct


def test_filter_5():
    template = '''{{ x|list|sort|first }}'''
    ast = parse(template).find(nodes.Filter)
    rtype, struct = visit_filter(ast, get_context(ast), {}, test_config)

    expected_struct = Dictionary({
        'x': Scalar(label='x', linenos=[1]),
    })
    assert struct == expected_struct


def test_filter_6():
    template = '''{{ x|unknownfilter }}'''
    ast = parse(template).find(nodes.Filter)
    with pytest.raises(InvalidExpression):
        visit_filter(ast, get_context(ast), {}, test_config)


def test_filter_7():
    template = '''{{ x|first|list }}'''
    ast = parse(template).find(nodes.Filter)
    with pytest.raises(UnexpectedExpression):
        visit_filter(ast, get_context(ast), {}, test_config)


def test_filter_8():
    ast = parse('{{ x|abs }}').find(nodes.Filter)
    rtype, struct = visit_filter(ast, get_context(ast), {}, test_config)
    assert rtype == Number(label='x', linenos=[1])
    assert struct == Dictionary({
        'x': Number(label='x', linenos=[1])
    })

    ast = parse('{{ x|striptags }}').find(nodes.Filter)
    rtype, struct = visit_filter(ast, get_context(ast), {}, test_config)
    assert rtype == String(label='x', linenos=[1])
    assert struct == Dictionary({
        'x': String(label='x', linenos=[1])
    })

    ast = parse('{{ x|wordcount }}').find(nodes.Filter)
    rtype, struct = visit_filter(ast, get_context(ast), {}, test_config)
    assert rtype == Number(label='x', linenos=[1])
    assert struct == Dictionary({
        'x': String(label='x', linenos=[1])
    })

    ast = parse('{{ xs|join("|") }}').find(nodes.Filter)
    rtype, struct = visit_filter(ast, get_context(ast), {}, test_config)
    assert rtype == String(label='xs', linenos=[1])
    assert struct == Dictionary({
        'xs': List(String(), label='xs', linenos=[1])
    })