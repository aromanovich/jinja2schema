from jinja2 import nodes
from jinja2schema.core import (parse, infer, Context, MergeException, visit_assign, visit_if, visit_for)
from jinja2schema.model import Dictionary, Scalar, List, Unknown, Tuple
import pytest

from .util import assert_structures_equal

def get_context(predicted_struct=None):
    return Context(return_struct=Scalar(), predicted_struct=predicted_struct or Scalar())


def test_for_1():
    template = '''
    {% for x in a.b %}
        {{ x }}
    {% endfor %}
    '''
    ast = parse(template).find(nodes.For)
    struct = visit_for(ast, get_context())
    expected_struct = Dictionary({
        'a': Dictionary({
            'b': List(Scalar(linenos=[3]), linenos=[2])
        }, linenos=[2]),
    })
    assert_structures_equal(struct, expected_struct)


def test_for_2():
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


def test_for_3():
    template = '''
    {% for a, b in list %}
        {{ a.field }}
        {{ b }}
    {% endfor %}
    '''
    ast = parse(template).find(nodes.For)
    struct = visit_for(ast, get_context())

    expected_struct = Dictionary({
        'list': List(Tuple((
            Dictionary({
                'field': Scalar(required=True, linenos=[3])
            }, linenos=[3]),
            Scalar(required=True, linenos=[4])
        ), linenos=[2]), linenos=[2])
    }, required=True, constant=False)
    assert_structures_equal(struct, expected_struct)


def test_assign_1():
    template = '''{% set a = b %}'''
    ast = parse(template).find(nodes.Assign)

    struct = visit_assign(ast, get_context())
    expected_struct = Dictionary({
        'a': Unknown(constant=True),
        'b': Unknown()
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)


def test_assign_2():
    template = '''{% set y = "-" ~ y %}'''
    ast = parse(template).find(nodes.Assign)

    struct = visit_assign(ast, get_context())
    expected_struct = Dictionary({
        'y': Scalar()
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)


def test_assign_3():
    template = '''{% set a, b = {'a': 1, 'b': 2} %}'''
    ast = parse(template).find(nodes.Assign)
    with pytest.raises(MergeException):
        visit_assign(ast, get_context())
    #struct = visit_assign(ast, get_context())
    #assert_structures_equal(struct, Dictionary({
    #    'a': Unknown(constant=True),
    #    'b': Unknown(constant=True),
    #}), check_linenos=False)


def test_assign_4():
    template = '''{% set a, b = 1, {'gsom': 'gsom', z: z} %}'''
    ast = parse(template).find(nodes.Assign)

    struct = visit_assign(ast, get_context())
    expected_struct = Dictionary({
        'a': Scalar(constant=True),
        'b': Dictionary(data={
            'gsom': Scalar(constant=True),
        }, constant=True),
        'z': Scalar(),
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)


def test_assign_5():
    template = '''
    {%- set weights = [
        ('A', {'data': 0.3}),
        ('B', {'data': 0.9}),
    ] %}
    '''
    ast = parse(template).find(nodes.Assign)
    struct = visit_assign(ast, get_context())
    expected_struct = Dictionary({
        'weights': List(Tuple([
            Scalar(constant=True),
            Dictionary({
                'data': Scalar(constant=True)
            }, constant=True),
        ], constant=True), constant=True)
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)


def test_assign_6():
    template = '''
    {%- set weights = [
        ('A', {'data': 0.3}),
        ('B', {'data': 0.9}, 1, 2),
    ] %}
    '''
    ast = parse(template).find(nodes.Assign)
    with pytest.raises(MergeException):
        visit_assign(ast, get_context())


def test_if_1():
    template = '''
    {% if (x or y) and not z %}
        {{ x }}
        {{ z.field }}
    {% endif %}
    '''
    ast = parse(template).find(nodes.If)
    struct = visit_if(ast, get_context())

    expected_struct = Dictionary({
        'z': Dictionary({
            'field': Scalar(linenos=[4]),
        }, linenos=[2, 4]),
        'x': Scalar(linenos=[2, 3]),
        'y': Unknown(linenos=[2]),
    })
    assert_structures_equal(struct, expected_struct)


def test_if_2():
    template = '''
    {% if z > x > y %}
    {% endif %}
    {% if x == y and x == 'asd' and z == 5 %}
    {% endif %}
    {{ x }}
    '''
    struct = infer(parse(template))

    expected_struct = Dictionary({
        'x': Scalar(linenos=[2, 4, 6]),
        'y': Unknown(linenos=[2, 4]),
        'z': Unknown(linenos=[2, 4]),
    })
    assert_structures_equal(struct, expected_struct)