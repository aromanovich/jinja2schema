from jinja2 import nodes
from jinja2schema.core import (parse, Context, visit_getitem, visit_cond_expr,
                               visit_getattr, visit_compare)
from jinja2schema.model import Dictionary, Scalar, List
from .util import assert_structures_equal, assert_rtypes_equal


def test_cond_expr():
    templates = (
        '''{{ queue if queue is defined else 'wizard' }}''',
        '''{{ queue if queue is undefined else 'wizard' }}'''
    )
    for template in templates:
        ast = parse(template).find(nodes.CondExpr)
        rtype, struct = visit_cond_expr(ast, Context())

        expected_struct = Dictionary({
            'queue': Scalar(may_be_defined=True)
        })
        assert_structures_equal(struct, expected_struct, check_linenos=False)

        expected_rtype = Scalar()
        assert_rtypes_equal(rtype, expected_rtype)


def test_getattr_1():
    template = '{{ (x or y).field.subfield[2].a }}'
    getattr_ast = parse(template).find(nodes.Getattr)
    rtype, struct = visit_getattr(getattr_ast, Context())

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
    rtype, struct = visit_getattr(getattr_ast, Context())

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
    template = '''{{ a[z][1:2][1].x }}'''
    ast = parse(template).find(nodes.Getattr)
    rtype, struct = visit_getattr(ast, Context())

    expected_struct = Dictionary({
        'a': List(List(List(Dictionary({'x': Scalar()})))),
        'z': Scalar()
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)


def test_getitem_1():
    template = '''{{ a['b']['c'][1]['d'][x] }}'''
    ast = parse(template).find(nodes.Getitem)
    rtype, struct = visit_getitem(ast, Context())

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
    rtype, struct = visit_compare(compare_ast, Context())

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
    rtype, struct = visit_compare(compare_ast, Context())

    expected_struct = Dictionary({
        'a': Scalar(),
        'b': List(Scalar()),
        'c': Scalar(),
        'x': Scalar(),
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)

    expected_rtype = Scalar()
    assert_rtypes_equal(rtype, expected_rtype)
