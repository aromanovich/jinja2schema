from jinja2 import nodes
import pytest

from jinja2schema.core import (parse, infer, Context, MergeException, UnexpectedExpression,
                               visit_assign, visit_if, visit_for)
from jinja2schema.model import Dictionary, Scalar, List, Unknown, Tuple


def test_for_1():
    template = '''
    {% for x in a.b %}
        {{ x }}
    {% endfor %}
    '''
    ast = parse(template).find(nodes.For)
    struct = visit_for(ast)
    expected_struct = Dictionary({
        'a': Dictionary({
            'b': List(Scalar(linenos=[3]), linenos=[2])
        }, linenos=[2]),
    })
    assert struct == expected_struct


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
    assert struct == expected_struct


def test_for_3():
    template = '''
    {% for a, b in list %}
        {{ a.field }}
        {{ b }}
    {% endfor %}
    '''
    ast = parse(template).find(nodes.For)
    struct = visit_for(ast)

    expected_struct = Dictionary({
        'list': List(Tuple((
            Dictionary({
                'field': Scalar(required=True, linenos=[3])
            }, linenos=[3]),
            Scalar(required=True, linenos=[4])
        ), linenos=[2]), linenos=[2])
    }, required=True, constant=False)
    assert struct == expected_struct


def test_assign_1():
    template = '''{% set a = b %}'''
    ast = parse(template).find(nodes.Assign)

    struct = visit_assign(ast)
    expected_struct = Dictionary({
        'a': Unknown(constant=True),   # TODO linenos
        'b': Unknown()
    })
    assert struct == expected_struct


def test_assign_2():
    template = '''{% set y = "-" ~ y %}'''
    ast = parse(template).find(nodes.Assign)

    struct = visit_assign(ast)
    expected_struct = Dictionary({
        'y': Scalar(linenos=[1])
    })
    assert struct == expected_struct


def test_assign_3():
    template = '''{% set a, b = {'a': 1, 'b': 2} %}'''
    ast = parse(template).find(nodes.Assign)
    with pytest.raises(UnexpectedExpression):
        visit_assign(ast)


def test_assign_4():
    template = '''{% set a, b = 1, {'gsom': 'gsom', z: z} %}'''
    ast = parse(template).find(nodes.Assign)

    struct = visit_assign(ast)
    expected_struct = Dictionary({
        'a': Scalar(linenos=[1], constant=True),
        'b': Dictionary(data={
            'gsom': Scalar(linenos=[1], constant=True),
        }, linenos=[1], constant=True),
        'z': Scalar(linenos=[1]),
    })
    assert struct == expected_struct


def test_assign_5():
    template = '''
    {%- set weights = [
        ('A', {'data': 0.3}),
        ('B', {'data': 0.9}),
    ] %}
    '''
    ast = parse(template).find(nodes.Assign)
    struct = visit_assign(ast)
    expected_struct = Dictionary({
        'weights': List(Tuple([
            Scalar(linenos=[3, 4], constant=True),
            Dictionary({
                'data': Scalar(linenos=[3, 4], constant=True)
            }, linenos=[3, 4], constant=True),
        ], linenos=[3, 4], constant=True), linenos=[2], constant=True)
    })
    assert struct == expected_struct


def test_assign_6():
    template = '''
    {%- set weights = [
        ('A', {'data': 0.3}),
        ('B', {'data': 0.9}, 1, 2),
    ] %}
    '''
    ast = parse(template).find(nodes.Assign)
    with pytest.raises(MergeException):
        visit_assign(ast)


def test_if_1():
    template = '''
    {% if (x or y) and not z %}
        {{ x }}
        {{ z.field }}
    {% endif %}
    '''
    ast = parse(template).find(nodes.If)
    struct = visit_if(ast)

    expected_struct = Dictionary({
        'z': Dictionary({
            'field': Scalar(linenos=[4]),
        }, linenos=[2, 4]),
        'x': Scalar(linenos=[2, 3]),
        'y': Unknown(linenos=[2]),
    })
    assert struct == expected_struct


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
    assert struct == expected_struct