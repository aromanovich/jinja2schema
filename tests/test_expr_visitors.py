import pytest
from jinja2 import nodes
from jinja2schema.core import (parse, Context, MergeException, UnsupportedSyntax,
                               visit_getitem, visit_cond_expr, visit_test,
                               visit_getattr, visit_compare, visit_filter,
                               visit_call)
from jinja2schema.model import Dictionary, Scalar, List, Unknown
from .util import assert_structures_equal, assert_rtypes_equal


def get_context(predicted_struct=None):
    return Context(return_struct=Scalar(), predicted_struct=predicted_struct or Scalar())


def test_cond_expr():
    templates = (
        '''{{ queue if queue is defined else 'wizard' }}''',
        '''{{ queue if queue is undefined else 'wizard' }}'''
    )
    for template in templates:
        ast = parse(template).find(nodes.CondExpr)
        rtype, struct = visit_cond_expr(ast, get_context())

        expected_struct = Dictionary({
            'queue': Scalar(may_be_defined=True)
        })
        assert_structures_equal(struct, expected_struct, check_linenos=False)

        expected_rtype = Scalar()
        assert_rtypes_equal(rtype, expected_rtype)


def test_getattr_1():
    template = '{{ (x or y).field.subfield[2].a }}'
    getattr_ast = parse(template).find(nodes.Getattr)
    rtype, struct = visit_getattr(getattr_ast, get_context())

    expected_struct = Dictionary({
        'x': Dictionary({
            'field': Dictionary({
                'subfield': List(Dictionary({
                    'a': Scalar()
                })),
            }),
        }),
        'y': Dictionary({
            'field': Dictionary({
                'subfield': List(Dictionary({
                    'a': Scalar()
                })),
            }),
        })
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)

    expected_rtype = Scalar()
    assert_rtypes_equal(rtype, expected_rtype)


def test_getattr_2():
    template = '{{ data.field.subfield }}'
    getattr_ast = parse(template).find(nodes.Getattr)
    rtype, struct = visit_getattr(getattr_ast, get_context())

    expected_struct = Dictionary({
        'data': Dictionary({
            'field': Dictionary({
                'subfield': Scalar(),
            }),
        }),
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)

    expected_rtype = Scalar()
    assert_rtypes_equal(rtype, expected_rtype)


def test_getattr_3():
    template = '''{{ a[z][1:n][1].x }}'''
    ast = parse(template).find(nodes.Getattr)
    rtype, struct = visit_getattr(ast, get_context())

    expected_struct = Dictionary({
        'a': List(List(List(Dictionary({'x': Scalar()})))),
        'z': Scalar(),
        'n': Scalar()
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)


def test_getitem_1():
    template = '''{{ a['b']['c'][1]['d'][x] }}'''
    ast = parse(template).find(nodes.Getitem)
    rtype, struct = visit_getitem(ast, get_context())

    expected_struct = Dictionary({
        'a': Dictionary({
            'b': Dictionary({
                'c': List(Dictionary({
                    'd': List(Scalar())
                })),
            }),
        }),
        'x': Scalar(),
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)

    expected_rtype = Scalar()
    assert_rtypes_equal(rtype, expected_rtype)


def test_compare_1():
    template = '{{ a < b < c }}'
    compare_ast = parse(template).find(nodes.Compare)
    rtype, struct = visit_compare(compare_ast, get_context())

    expected_struct = Dictionary({
        'a': Scalar(),
        'b': Scalar(),
        'c': Scalar(),
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)

    expected_rtype = Scalar()
    assert_rtypes_equal(rtype, expected_rtype)


def test_compare_2():
    template = '{{ a + b[1] - c == 4 == x }}'
    compare_ast = parse(template).find(nodes.Compare)
    rtype, struct = visit_compare(compare_ast, get_context())

    expected_struct = Dictionary({
        'a': Scalar(),
        'b': List(Scalar()),
        'c': Scalar(),
        'x': Scalar(),
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)

    expected_rtype = Scalar()
    assert_rtypes_equal(rtype, expected_rtype)


def test_filter_1():
    template = '{{ x|striptags }}'
    filter_ast = parse(template).find(nodes.Filter)
    rtype, struct = visit_filter(filter_ast, get_context())

    expected_struct = Dictionary({'x': Scalar()})
    assert_structures_equal(struct, expected_struct)


def test_filter_2():
    with pytest.raises(MergeException):
        template = '''{{ items|batch(3, '&nbsp;') }}'''
        filter_ast = parse(template).find(nodes.Filter)
        visit_filter(filter_ast, get_context())


def test_filter_3():
    template = '''{{ x|default('g') }}'''
    filter_ast = parse(template).find(nodes.Filter)
    rtype, struct = visit_filter(filter_ast, get_context())

    expected_struct = Dictionary({'x': Scalar(used_with_default=True)})
    assert_structures_equal(struct, expected_struct, check_linenos=False)


def test_filter_4():
    template = '''{{ (xs|first|last).gsom|sort|length }}'''
    filter_ast = parse(template).find(nodes.Filter)
    rtype, struct = visit_filter(filter_ast, get_context())

    expected_struct = Dictionary({
        'xs': List(List(Dictionary({
            'gsom': List(Unknown(linenos=[1])),
        }))),
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)


def test_filter_5():
    template = '''{{ x|list|sort|first }}'''
    filter_ast = parse(template).find(nodes.Filter)
    rtype, struct = visit_filter(filter_ast, get_context())

    expected_struct = Dictionary({
        'x': Scalar(),
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)


def test_filter_6():
    template = '''{{ x|unknownfilter }}'''
    filter_ast = parse(template).find(nodes.Filter)
    with pytest.raises(UnsupportedSyntax):
        visit_filter(filter_ast, get_context())


def test_filter_7():
    template = '''{{ x|first|list }}'''
    filter_ast = parse(template).find(nodes.Filter)
    with pytest.raises(MergeException):
        visit_filter(filter_ast, get_context())


def test_test_1():
    template = '''{{ x is divisibleby data.field }}'''
    test_ast = parse(template).find(nodes.Test)
    rtype, struct = visit_test(test_ast, get_context())

    expected_struct = Dictionary({
        'x': Scalar(),
        'data': Dictionary({
            'field': Scalar(),
        })
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)

    template = '''{{ x is divisibleby 3 }}'''
    test_ast = parse(template).find(nodes.Test)
    rtype, struct = visit_test(test_ast, get_context())

    expected_struct = Dictionary({
        'x': Scalar(),
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)

def test_test_2():
    template = '''{{ x is string }}'''
    test_ast = parse(template).find(nodes.Test)
    rtype, struct = visit_test(test_ast, get_context())

    expected_struct = Dictionary({
        'x': Unknown()
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)


def test_call_dict():
    template = '''{{ dict(x=dict(a=1, b=2).c) }}'''
    call_ast = parse(template).find(nodes.Call)
    rtype, struct = visit_call(call_ast, get_context(predicted_struct=Unknown()))
    expected_rtype = Dictionary({
        'x': Dictionary({
            'a': Scalar(constant=True),
            'b': Scalar(constant=True)
        }, constant=True)
    }, constant=True)
    assert_rtypes_equal(rtype, expected_rtype)