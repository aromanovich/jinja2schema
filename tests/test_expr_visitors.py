import pytest
from jinja2 import nodes

from jinja2schema.core import (parse, Context, MergeException, UnsupportedSyntax, UnexpectedExpression,
                               visit_getitem, visit_cond_expr, visit_test,
                               visit_getattr, visit_compare, visit_filter,
                               visit_call)
from jinja2schema.model import Dictionary, Scalar, List, Unknown


def get_context(ast):
    return Context(return_struct=Scalar(), predicted_struct=Scalar.from_ast(ast))


def test_cond_expr():
    templates = (
        '''{{ queue if queue is defined else 'wizard' }}''',
        '''{{ queue if queue is undefined else 'wizard' }}'''
    )
    for template in templates:
        ast = parse(template).find(nodes.CondExpr)
        rtype, struct = visit_cond_expr(ast, get_context(ast))

        expected_struct = Dictionary({
            'queue': Scalar(linenos=[1], may_be_defined=True)
        })
        assert struct == expected_struct


def test_getattr_1():
    template = '{{ (x or y).field.subfield[2].a }}'
    ast = parse(template).find(nodes.Getattr)
    rtype, struct = visit_getattr(ast, get_context(ast))

    expected_struct = Dictionary({
        'x': Dictionary({
            'field': Dictionary({
                'subfield': List(Dictionary({
                    'a': Scalar(linenos=[1])
                }, linenos=[1]), linenos=[1]),
            }, linenos=[1]),
        }, linenos=[1]),
        'y': Dictionary({
            'field': Dictionary({
                'subfield': List(Dictionary({
                    'a': Scalar(linenos=[1])
                }, linenos=[1]), linenos=[1]),
            }, linenos=[1]),
        }, linenos=[1])
    })
    assert struct == expected_struct


def test_getattr_2():
    template = '{{ data.field.subfield }}'
    ast = parse(template).find(nodes.Getattr)
    rtype, struct = visit_getattr(ast, get_context(ast))

    expected_struct = Dictionary({
        'data': Dictionary({
            'field': Dictionary({
                'subfield': Scalar(linenos=[1]),
            }, linenos=[1]),
        }, linenos=[1]),
    })
    assert struct == expected_struct


def test_getattr_3():
    template = '''{{ a[z][1:\nn][1].x }}'''
    ast = parse(template).find(nodes.Getattr)
    rtype, struct = visit_getattr(ast, get_context(ast))

    expected_struct = Dictionary({
        'a': List(
            List(
                List(
                    Dictionary({
                        'x': Scalar(linenos=[2])
                    }, linenos=[2]),
                    linenos=[2]),
                linenos=[1]
            ),
            linenos=[1]
        ),
        'z': Scalar(linenos=[1]),
        'n': Scalar(linenos=[2])
    })
    assert struct == expected_struct


def test_getitem_1():
    template = '''{{ a['b']['c'][1]['d'][x] }}'''
    ast = parse(template).find(nodes.Getitem)
    rtype, struct = visit_getitem(ast, get_context(ast))

    expected_struct = Dictionary({
        'a': Dictionary({
            'b': Dictionary({
                'c': List(Dictionary({
                    'd': List(Scalar(linenos=[1]), linenos=[1])
                }, linenos=[1]), linenos=[1]),
            }, linenos=[1]),
        }, linenos=[1]),
        'x': Scalar(linenos=[1]),
    })
    assert struct == expected_struct


def test_compare_1():
    template = '{{ a < b < c }}'
    ast = parse(template).find(nodes.Compare)
    rtype, struct = visit_compare(ast, get_context(ast))

    expected_struct = Dictionary({
        'a': Scalar(linenos=[1]),
        'b': Scalar(linenos=[1]),
        'c': Scalar(linenos=[1]),
    })
    assert struct == expected_struct


def test_compare_2():
    template = '{{ a + b[1] - c == 4 == x }}'
    ast = parse(template).find(nodes.Compare)
    rtype, struct = visit_compare(ast, get_context(ast))

    expected_struct = Dictionary({
        'a': Scalar(linenos=[1]),
        'b': List(Scalar(linenos=[1]), linenos=[1]),
        'c': Scalar(linenos=[1]),
        'x': Scalar(linenos=[1]),
    })
    assert struct == expected_struct


def test_filter_1():
    template = '{{ x|striptags }}'
    ast = parse(template).find(nodes.Filter)
    rtype, struct = visit_filter(ast, get_context(ast))

    expected_struct = Dictionary({'x': Scalar(linenos=[1])})
    assert struct == expected_struct


def test_filter_2():
    template = '''{{ items|batch(3, '&nbsp;') }}'''
    ast = parse(template).find(nodes.Filter)
    with pytest.raises(UnexpectedExpression):
        visit_filter(ast, get_context(ast))


def test_filter_3():
    template = '''{{ x|default('g') }}'''
    ast = parse(template).find(nodes.Filter)
    rtype, struct = visit_filter(ast, get_context(ast))

    expected_struct = Dictionary({'x': Scalar(linenos=[1], used_with_default=True)})
    assert struct == expected_struct


def test_filter_4():
    template = '''{{ (xs|first|last).gsom|sort|length }}'''
    ast = parse(template).find(nodes.Filter)
    rtype, struct = visit_filter(ast, get_context(ast))

    expected_struct = Dictionary({
        'xs': List(List(Dictionary({
            'gsom': List(Unknown(), linenos=[1]),
        }, linenos=[1]), linenos=[1]), linenos=[1]),
    })
    assert struct == expected_struct


def test_filter_5():
    template = '''{{ x|list|sort|first }}'''
    ast = parse(template).find(nodes.Filter)
    rtype, struct = visit_filter(ast, get_context(ast))

    expected_struct = Dictionary({
        'x': Scalar(linenos=[1]),
    })
    assert struct == expected_struct


def test_filter_6():
    template = '''{{ x|unknownfilter }}'''
    ast = parse(template).find(nodes.Filter)
    with pytest.raises(UnsupportedSyntax):
        visit_filter(ast, get_context(ast))


def test_filter_7():
    template = '''{{ x|first|list }}'''
    ast = parse(template).find(nodes.Filter)
    with pytest.raises(UnexpectedExpression):
        visit_filter(ast, get_context(ast))


def test_test_1():
    template = '''{{ x is divisibleby data.field }}'''
    ast = parse(template).find(nodes.Test)
    rtype, struct = visit_test(ast, get_context(ast))

    expected_struct = Dictionary({
        'x': Scalar(linenos=[1]),
        'data': Dictionary({
            'field': Scalar(linenos=[1]),
        }, linenos=[1])
    })
    assert struct == expected_struct

    template = '''{{ x is divisibleby 3 }}'''
    ast = parse(template).find(nodes.Test)
    rtype, struct = visit_test(ast, get_context(ast))

    expected_struct = Dictionary({
        'x': Scalar(linenos=[1]),
    })
    assert struct == expected_struct


def test_test_2():
    template = '''{{ x is string }}'''
    ast = parse(template).find(nodes.Test)
    rtype, struct = visit_test(ast, get_context(ast))

    expected_struct = Dictionary({
        'x': Unknown(linenos=[1])
    })
    assert struct == expected_struct


def test_call_dict():
    template = '''{{ dict(x=\ndict(\na=1, b=2)) }}'''
    call_ast = parse(template).find(nodes.Call)
    rtype, struct = visit_call(
        call_ast, Context(predicted_struct=Unknown.from_ast(call_ast)))
    expected_rtype = Dictionary({
        'x': Dictionary({
            'a': Scalar(linenos=[3], constant=True),
            'b': Scalar(linenos=[3], constant=True)
        }, linenos=[2], constant=True)
    }, linenos=[1], constant=True)
    assert rtype == expected_rtype