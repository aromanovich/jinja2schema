import pytest

from jinja2schema.core import parse, infer, Context
from jinja2schema.core import *
from jinja2schema.model import Dictionary, Scalar, List, Unknown, Tuple


def assert_rtypes_equal(a, b):
    assert_structures_equal(a, b, check_required=False, check_linenos=False)


def assert_structures_equal(a, b, check_required=True, check_linenos=True):
    assert type(a) is type(b)
    if check_required:
        assert a.required == b.required
    assert a.constant == b.constant
    if check_linenos:
        assert set(a.linenos) == set(b.linenos)
    if isinstance(a, Dictionary):
        assert set(a.keys()) == set(b.keys())
        for key in a.keys():
            assert_structures_equal(a[key], b[key], check_required=check_required, check_linenos=check_linenos)
    elif isinstance(a, List):
        assert_structures_equal(a.el_struct, b.el_struct, check_required=check_required, check_linenos=check_linenos)
    elif isinstance(a, Tuple):
        assert len(a.el_structs) == len(b.el_structs)
        for x, y in zip(a.el_structs, b.el_structs):
            assert_structures_equal(x, y, check_required=check_required, check_linenos=check_linenos)


def test_basics():
    template = '''
    {% if (x or y) and not z %}
        {{ x }}
        {{ z.field }}
    {% endif %}
    '''
    ast = parse(template)
    struct = infer(ast)

    expected_struct = Dictionary({
        'z': Dictionary({
            'field': Scalar(linenos=[4]),
        }, linenos=[2, 4]),
        'x': Scalar(linenos=[2, 3]),
        'y': Unknown(linenos=[2]),
    })
    assert_structures_equal(struct, expected_struct)

    template = '''
        {% for x in xs %}
            {{ x }}
            {% for y in ys %}
                {{ loop.index0 }}
            {% endfor %}
            {{ loop.length }}
        {% endfor %}
    '''
    ast = parse(template)
    struct = infer(ast)

    expected_struct = Dictionary({
        'xs': List(Scalar(linenos=[3]), linenos=[2]),
        'ys': List(Unknown(linenos=[4]), linenos=[4]),
    })
    assert_structures_equal(struct, expected_struct)

    template = '''
        {% if z > x > y %}
        {% endif %}
        {% if x == y and x == 'asd' and z == 5 %}
        {% endif %}
        {{ x }}
    '''
    ast = parse(template)
    struct = infer(ast)

    expected_struct = Dictionary({
        'x': Scalar(linenos=[2, 4, 6]),
        'y': Unknown(linenos=[2, 4]),
        'z': Unknown(linenos=[2, 4]),
    })
    assert_structures_equal(struct, expected_struct)


def test_may_be_defined():
    template = '''
    {% if x is undefined %}
        {% set x = 'atata' %}
    {% endif %}
    {{ x }}

    {% if y is defined %}
        {# pass #}
    {% else %}
        {% set y = 'atata' %}
    {% endif %}
    {{ y }}
    '''
    ast = parse(template)
    struct = infer(ast)

    expected_struct = Dictionary({
        'x': Scalar(linenos=[2, 3, 5], constant=False, may_be_defined=True),
        'y': Scalar(linenos=[10, 12, 7], constant=False, may_be_defined=True),
    })
    assert_structures_equal(struct, expected_struct)

    template = '''
    {{ x }}
    {% if x is undefined %}
        {% set x = 'atata' %}
    {% endif %}
    {{ x }}
    '''
    ast = parse(template)
    struct = infer(ast)
    expected_struct = Dictionary({
        'x': Scalar(linenos=[2, 3, 4, 6], constant=False, may_be_defined=False),
    })
    assert_structures_equal(struct, expected_struct)


def test_1():
    template = '''
    {% set d = {'x': 123, a: z.qwerty} %}
    {{ d.x }}
    '''
    ast = parse(template)
    struct = infer(ast)
    expected_struct = Dictionary({
        'a': Scalar(linenos=[2]),
        'z': Dictionary(data={
            'qwerty': Unknown(linenos=[2]),
        }, linenos=[2]),
    })
    assert_structures_equal(struct, expected_struct)


def test_2():
    template = '''
    {% set d = {'x': 123, a: z.qwerty} %}
    {{ d.x.field }}
    '''
    ast = parse(template)
    with pytest.raises(Exception):
        infer(ast)


def test_3():
    template = '''
    {% if test1 %}
        {% if test2 %}
            {% set d = {'x': 123, a: z.qwerty} %}
        {% else %}
            {% set d = {'x': 456, a: z.gsom} %}
        {% endif %}
    {% endif %}
    {% if d %}
        {{ d.x }}
    {% endif %}
    {{ z.gsom }}
    '''
    ast = parse(template)
    struct = infer(ast)
    expected_struct = Dictionary({
        'a': Scalar(linenos=[4, 6]),
        'test1': Unknown(linenos=[2]),
        'test2': Unknown(linenos=[3]),
        'z': Dictionary(data={
            'qwerty': Unknown(linenos=[4]),
            'gsom': Scalar(linenos=[6, 12]),
        }, linenos=[4, 6, 12]),
    })
    assert_structures_equal(struct, expected_struct)


def test_4():
    template = '''
    {% if test1 %}
        {% if test2 %}
            {% set x = '123' %}
        {% endif %}
    {% endif %}
    {{ x.test }}
    '''
    ast = parse(template)
    with pytest.raises(Exception):
        struct = infer(ast)


def test_5():
    template = '''
    {% if x %}
        {% set x = '123' %}
    {% else %}
        {% set x = '456' %}
    {% endif %}
    {{ x }}
    '''
    ast = parse(template)
    struct = infer(ast)


def test_tuple_unpacking():
    template = '''
    {% for a, b in list %}
        {{ a.field }}
        {{ b }}
    {% endfor %}
    {% set a, b = list[0] %}
    '''
    ast = parse(template)
    struct = infer(ast)
    expected_struct = Dictionary({
        'list': List(Tuple((
            Dictionary({
                'field': Scalar(required=True, linenos=[3])
            }, linenos=[3]),
            Scalar(required=True, linenos=[4])
        ), linenos=[2, 6]), linenos=[2, 6])
    }, required=True, constant=False)
    assert_structures_equal(struct, expected_struct)


def x(template):
    ast = parse(template)
    return ast.body[0]





def test_dict():
    template = '''
    {% set a = {'x': 123} %}
    {% set b = {a: 'test'} %}
    '''
    ast = parse(template)
    with pytest.raises(Exception):
        struct = infer(ast)


def test_getattr():
    template = '{{ (x or y).field.subfield[2].a }}'
    getattr_ast = x(template).nodes[0]
    rtype, struct = visit_getattr(getattr_ast, Context())

    expected_rtype = Scalar()
    assert_rtypes_equal(rtype, expected_rtype)
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

    template = '{{ data.field.subfield }}'
    getattr_ast = x(template).nodes[0]
    rtype, struct = visit_getattr(getattr_ast, Context())

    expected_rtype = Scalar()
    assert_rtypes_equal(rtype, expected_rtype)

    expected_struct = Dictionary({
        'data': Dictionary({
            'field': Dictionary({
                'subfield': Scalar(),
            }),
        }),
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)


def test_compare():
    template = '{{ a < b < c }}'
    compare_ast = x(template).nodes[0]
    rtype, struct = visit_compare(compare_ast, Context())

    expected_rtype = Scalar()
    assert_rtypes_equal(rtype, expected_rtype)

    expected_struct = Dictionary({
        'a': Scalar(),
        'b': Scalar(),
        'c': Scalar(),
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)

    template = '{{ a + b[1] - c == 4 == x }}'
    compare_ast = x(template).nodes[0]
    rtype, struct = visit_compare(compare_ast, Context())

    expected_rtype = Scalar()
    assert_rtypes_equal(rtype, expected_rtype)

    expected_struct = Dictionary({
        'a': Scalar(),
        'b': List(Scalar()),
        'c': Scalar(),
        'x': Scalar(),
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)


def test_getitem():
    template = '''{{ a['b']['c'][1]['d'][x] }}'''
    ast = x(template).nodes[0]
    rtype, struct = visit_getitem(ast, Context())

    expected_rtype = Scalar()
    assert_rtypes_equal(rtype, expected_rtype)

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

    template = '''{{ a[z][1:2][1].x }}'''
    ast = x(template).nodes[0]
    rtype, struct = visit_getattr(ast, Context())

    expected_struct = Dictionary({
        'a': List(List(List(Dictionary({'x': Scalar()})))),
        'z': Scalar()
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)


def test_visit_for():
    template = '''{% for x in a.b %}{{ x }}{% endfor %}'''
    ast = x(template)
    struct = visit_for(ast, Context())
    expected_struct = Dictionary({
        'a': Dictionary({
            'b': List(Scalar())
        }),
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)


def test_assign():
    template = '''{% set a = b %}'''
    ast = x(template)
    struct = visit_assign(ast, Context())
    expected_struct = Dictionary({
        'a': Unknown(constant=True),
        'b': Unknown()
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)

    template = '{% set y = "-" ~ y %}'
    ast = x(template)
    struct = visit_assign(ast, Context())
    expected_struct = Dictionary({
        'y': Scalar()
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)

    template = '''{% set a, b = {'a': 1, 'b': 2} %}'''
    ast = x(template)
    struct = visit_assign(ast, Context())
    assert_structures_equal(struct, Dictionary({
        'a': Unknown(constant=True),
        'b': Unknown(constant=True),
    }), check_linenos=False)

    template = '''{% set a, b = 1, {'gsom': 'gsom', z: z} %}'''
    ast = x(template)
    struct = visit_assign(ast, Context())
    expected_struct = Dictionary({
        'a': Scalar(constant=True),
        'b': Dictionary(data={
            'gsom': Scalar(constant=True),
        }, constant=True),
        'z': Scalar(),
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)

    template = '''
    {%- set weights = [
        ('A', {'data': 0.3}),
        ('B', {'data': 0.9}),
    ] %}
    '''
    ast = x(template)
    struct = visit_assign(ast, Context())
    expected_struct = Dictionary({
        'weights': List(Tuple([
            Scalar(constant=True),
            Dictionary({
                'data': Scalar(constant=True)
            }, constant=True),
        ], constant=True), constant=True)
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)


@pytest.mark.xfail
def test_assign_invalid():
    template = '''
    {%- set weights = [
        ('A', {'data': 0.3}),
        ('B', {'data': [0.9]}),
    ] %}
    '''
    ast = x(template)
    with pytest.raises(Exception):
        visit_assign(ast, Context())


def test_cond_expr():
    templates = (
        '''{{ queue if queue is defined else 'wizard' }}''',
        '''{{ queue if queue is undefined else 'wizard' }}'''
    )
    for template in templates:
        ast = x(template).nodes[0]
        rtype, struct = visit_cond_expr(ast, Context())

        expected_struct = Dictionary({
            'queue': Scalar(constant=False, may_be_defined=False)
        })
        expected_rtype = Scalar(constant=False, may_be_defined=True)
        assert_structures_equal(struct, expected_struct, check_linenos=False)
        assert_rtypes_equal(rtype, expected_rtype)


def test_qqq():
    template = '''
{%- set xys = [
  ("a", 0.3),
  ("b", 0.3),
] %}
{% if configuration is undefined %}
  {% set configuration = 'prefix-' ~ timestamp %}
{% endif %}
queue: {{ queue if queue is defined else 'wizard' }}
description: >-
  {%- for x, y in xys %}
    {{ loop.index }}:
    {{ x }} {{ y }}
  {%- endfor %}
        '''
    ast = parse(template)
    struct = infer(ast)
