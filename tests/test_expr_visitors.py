# coding: utf-8
import pytest
from jinja2 import nodes

from jinja2schema.config import Config
from jinja2schema.core import parse
from jinja2schema.visitors.expr import (Context, visit_getitem, visit_cond_expr, visit_test,
                                        visit_getattr, visit_compare, visit_filter, visit_call, visit_dict)
from jinja2schema.exceptions import UnexpectedExpression, InvalidExpression
from jinja2schema.model import Dictionary, Scalar, List, Unknown, String, Number, Boolean, Tuple
from jinja2schema.util import debug_repr


test_config = Config()


def get_context(ast):
    return Context(return_struct_cls=Scalar, predicted_struct=Scalar.from_ast(ast))


def test_cond_expr():
    template = '''{{ queue if queue is defined else 'wizard' }}''',
    ast = parse(template).find(nodes.CondExpr)
    rtype, struct = visit_cond_expr(ast, get_context(ast), {}, test_config)

    expected_struct = Dictionary({
        'queue': Scalar(label='queue', linenos=[1], checked_as_defined=True)
    })
    assert struct == expected_struct

    template = '''{{ queue if queue is undefined else 'wizard' }}'''
    ast = parse(template).find(nodes.CondExpr)
    rtype, struct = visit_cond_expr(ast, get_context(ast), {}, test_config)

    expected_struct = Dictionary({
        'queue': Scalar(label='queue', linenos=[1], checked_as_undefined=True)
    })
    assert struct == expected_struct


def test_getattr_1():
    template = '{{ (x or y).field.subfield[2].a }}'
    ast = parse(template).find(nodes.Getattr)
    rtype, struct = visit_getattr(ast, get_context(ast), {}, test_config)

    x_or_y_dict = {
        'field': Dictionary({
            'subfield': List(Dictionary({
                'a': Scalar(label='a', linenos=[1])
            }, linenos=[1]), label='subfield', linenos=[1]),
        }, label='field', linenos=[1]),
    }

    expected_struct = Dictionary({
        'x': Dictionary(x_or_y_dict, label='x', linenos=[1]),
        'y': Dictionary(x_or_y_dict, label='y', linenos=[1])
    })
    assert struct == expected_struct


def test_getattr_2():
    template = '{{ data.field.subfield }}'
    ast = parse(template).find(nodes.Getattr)
    rtype, struct = visit_getattr(ast, get_context(ast), {}, test_config)

    expected_struct = Dictionary({
        'data': Dictionary({
            'field': Dictionary({
                'subfield': Scalar(label='subfield', linenos=[1]),
            }, label='field', linenos=[1]),
        }, label='data', linenos=[1]),
    })
    assert struct == expected_struct


def test_getattr_3():
    template = '''{{ a[z][1:\nn][1].x }}'''
    ast = parse(template).find(nodes.Getattr)
    config = Config()
    config.TYPE_OF_VARIABLE_INDEXED_WITH_VARIABLE_TYPE = 'list'
    rtype, struct = visit_getattr(ast, get_context(ast), {}, config)

    expected_struct = Dictionary({
        'a': List(
            List(
                List(
                    Dictionary({
                        'x': Scalar(label='x', linenos=[2])
                    }, linenos=[2]),
                    linenos=[2]),
                linenos=[1]
            ),
            label='a',
            linenos=[1]
        ),
        'z': Scalar(label='z', linenos=[1]),
        'n': Number(label='n', linenos=[2])
    })
    assert struct == expected_struct


def test_getitem_1():
    template = '''{{ a['b']['c'][1]['d'][x] }}'''
    ast = parse(template).find(nodes.Getitem)
    config = Config()
    config.TYPE_OF_VARIABLE_INDEXED_WITH_VARIABLE_TYPE = 'list'
    rtype, struct = visit_getitem(ast, get_context(ast), {}, config)

    expected_struct = Dictionary({
        'a': Dictionary({
            'b': Dictionary({
                'c': List(Dictionary({
                    'd': List(Scalar(linenos=[1]), label='d', linenos=[1])
                }, linenos=[1]), label='c', linenos=[1]),
            }, label='b', linenos=[1]),
        }, label='a', linenos=[1]),
        'x': Scalar(label='x', linenos=[1]),
    })
    assert struct == expected_struct


def test_getitem_2():
    template = '''{{ a[z] }}'''
    ast = parse(template).find(nodes.Getitem)
    config = Config()
    config.TYPE_OF_VARIABLE_INDEXED_WITH_VARIABLE_TYPE = 'dictionary'
    rtype, struct = visit_getitem(ast, get_context(ast), {}, config)

    expected_struct = Dictionary({
        'a': Dictionary(label='a', linenos=[1]),
        'z': Scalar(label='z', linenos=[1]),
    })
    assert struct == expected_struct


def test_getitem_3():
    template = '''{{ a[3] }}'''
    ast = parse(template).find(nodes.Getitem)
    config = Config()
    config.TYPE_OF_VARIABLE_INDEXED_WITH_INTEGER_TYPE = 'tuple'
    rtype, struct = visit_getitem(ast, get_context(ast), {}, config)

    expected_struct = Dictionary({
        'a': Tuple([
            Unknown(),
            Unknown(),
            Unknown(),
            Scalar(linenos=[1]),
        ], label='a', linenos=[1]),
    })
    assert struct == expected_struct


def test_compare_1():
    template = '{{ a < b < c }}'
    ast = parse(template).find(nodes.Compare)
    rtype, struct = visit_compare(ast, get_context(ast), {}, test_config)

    expected_struct = Dictionary({
        'a': Unknown(label='a', linenos=[1]),
        'b': Unknown(label='b', linenos=[1]),
        'c': Unknown(label='c', linenos=[1]),
    })
    assert struct == expected_struct


def test_compare_2():
    template = '{{ a + b[1] - c == 4 == x }}'
    ast = parse(template).find(nodes.Compare)
    rtype, struct = visit_compare(ast, get_context(ast), {}, test_config)
    # TODO make customizable
    expected_struct = Dictionary({
        'a': Unknown(label='a', linenos=[1]),
        'b': List(Unknown(linenos=[1]), label='b', linenos=[1]),
        'c': Unknown(label='c', linenos=[1]),
        'x': Unknown(label='x', linenos=[1]),
    })
    assert struct == expected_struct


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

def test_slice():
    template = '''{{ xs[a:2:b] }}'''
    ast = parse(template).find(nodes.Getitem)
    rtype, struct = visit_getitem(ast, get_context(ast), {}, test_config)
    assert struct == Dictionary({
        'xs': List(Scalar(linenos=[1]), label='xs', linenos=[1]),
        'a': Number(label='a', linenos=[1]),
        'b': Number(label='b', linenos=[1]),
    })


def test_test_1():
    template = '''{{ x is divisibleby data.field }}'''
    ast = parse(template).find(nodes.Test)
    rtype, struct = visit_test(ast, get_context(ast), {}, test_config)

    expected_struct = Dictionary({
        'x': Scalar(label='x', linenos=[1]),
        'data': Dictionary({
            'field': Number(label='field', linenos=[1]),
        }, label='data', linenos=[1])
    })

    assert struct == expected_struct

    template = '''{{ x is divisibleby 3 }}'''
    ast = parse(template).find(nodes.Test)
    rtype, struct = visit_test(ast, get_context(ast), {}, test_config)

    expected_struct = Dictionary({
        'x': Scalar(label='x', linenos=[1]),
    })
    assert struct == expected_struct


def test_test_2():
    template = '''{{ x is string }}'''
    ast = parse(template).find(nodes.Test)
    rtype, struct = visit_test(ast, get_context(ast), {}, test_config)

    expected_struct = Dictionary({
        'x': Unknown(label='x', linenos=[1])
    })
    assert struct == expected_struct


def test_call_dict():
    template = '''{{ dict(x=\ndict(\na=1, b=2)) }}'''
    call_ast = parse(template).find(nodes.Call)
    rtype, struct = visit_call(
        call_ast, Context(predicted_struct=Unknown.from_ast(call_ast)), {}, test_config)
    expected_rtype = Dictionary({
        'x': Dictionary({
            'a': Number(linenos=[3], constant=True),
            'b': Number(linenos=[3], constant=True)
        }, linenos=[2], constant=True)
    }, linenos=[1], constant=True)
    assert rtype == expected_rtype


def test_compare():
    template = '''{{ a < c }}'''
    compare_ast = parse(template).find(nodes.Compare)
    rtype, struct = visit_compare(compare_ast, get_context(compare_ast), {}, test_config)
    expected_rtype = Boolean(linenos=[1])
    assert rtype == expected_rtype
