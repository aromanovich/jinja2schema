# coding: utf-8
from jinja2schema.config import Config

from jinja2schema.core import infer
from jinja2schema.model import Dictionary, Scalar, Unknown, String, Boolean, Number


def test_1():
    template = '''
    {%- if x is undefined %}
        {{ test }}
    {%- endif %}

    {%- if y is undefined %}
        {% set y = 123 %}
    {%- endif %}

    {%- if y is defined %}
        {{ y }}
    {%- endif %}

    {%- if z is undefined %}
        {{ z }}
    {%- endif %}
    '''
    struct = infer(template)
    expected_struct = Dictionary({
        'x': Unknown(label='x', checked_as_undefined=True, linenos=[2]),
        'test': Scalar(label='test', linenos=[3]),
        'y': Number(label='y', may_be_defined=True, linenos=[6, 7, 10, 11]),
        'z': Scalar(label='z', linenos=[14, 15]),
    })
    assert struct == expected_struct


def test_2():
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
    struct = infer(template)
    expected_struct = Dictionary({
        'x': String(linenos=[2, 3, 5], label='x',
                    constant=False, may_be_defined=True),
        'y': String(linenos=[7, 10, 12], label='y',
                    constant=False, may_be_defined=True),
    })
    assert struct == expected_struct

    template = '''
    {{ x }}
    {% if x is undefined %}
        {% set x = 'atata' %}
    {% endif %}
    {{ x }}
    '''
    struct = infer(template)
    expected_struct = Dictionary({
        'x': String(linenos=[2, 3, 4, 6], label='x',
                    constant=False, may_be_defined=False),
    })
    assert struct == expected_struct


def test_3():
    config = Config(BOOLEAN_CONDITIONS=True)
    template = '''
    {%- if new_configuration is undefined %}
      {%- if production is defined and production %}
        {% set new_configuration = 'prefix-' ~ timestamp %}
      {%- else %}
        {% set new_configuration = 'prefix-' ~ timestamp %}
      {%- endif %}
    {%- endif %}
    '''
    struct = infer(template, config)
    expected_struct = Dictionary({
        'new_configuration': String(label='new_configuration', may_be_defined=True, checked_as_undefined=True, linenos=[2, 4, 6]),
        'production': Boolean(label='production', checked_as_defined=True, linenos=[3]),
        'timestamp': String(label='timestamp', linenos=[4, 6]),
    })
    assert struct == expected_struct


def test_4():
    template = '''{{ 'x and y' if x and y is defined else ':(' }}'''
    config = Config(BOOLEAN_CONDITIONS=True)
    struct = infer(template, config)
    expected_struct = Dictionary({
        'x': Boolean(label='x', linenos=[1]),
        'y': Unknown(label='y', checked_as_defined=True, linenos=[1]),
    })
    assert struct == expected_struct

    template = '''
    {% if x is defined and x.a == 'a' %}
        {{ x.b }}
    {% endif %}
    '''
    struct = infer(template, config)
    expected_struct = Dictionary({
        'x': Dictionary({
            'a': Unknown(label='a', linenos=[2]),
            'b': Scalar(label='b', linenos=[3]),

        }, label='x', checked_as_defined=True, linenos=[2, 3])
    })
    assert struct == expected_struct

    template = '''
    {% if x is undefined and x.a == 'a' %}
        {{ x.b }}
    {% endif %}
    '''
    struct = infer(template, config)
    expected_struct = Dictionary({
        'x': Dictionary({
            'a': Unknown(label='a', linenos=[2]),
            'b': Scalar(label='b', linenos=[3]),

        }, label='x', linenos=[2, 3])
    })
    assert struct == expected_struct

    template = '''
    {% if x is undefined %}
        none
    {% endif %}
    {{ x }}
    '''
    struct = infer(template, config)
    expected_struct = Dictionary({
        'x': Scalar(label='x', linenos=[2, 5]),
    })
    assert struct == expected_struct

    template = '''
    {% if x is defined %}
        none
    {% endif %}
    {{ x }}
    '''
    struct = infer(template, config)
    expected_struct = Dictionary({
        'x': Scalar(label='x', linenos=[2, 5]),
    })
    assert struct == expected_struct

    template = '''
    {% if x is defined %}
    {% else %}
        {{ x }}
    {% endif %}
    '''
    struct = infer(template, config)
    expected_struct = Dictionary({
        'x': Scalar(label='x', linenos=[2, 4]),
    })
    assert struct == expected_struct

    template = '''
    queue: {{ queue if queue is defined else 'wizard' }}
    queue: {{ queue if queue is defined else 'wizard' }}
    '''
    struct = infer(template, config)
    expected_struct = Dictionary({
        'queue': Scalar(label='queue', linenos=[2, 3], checked_as_defined=True)
    })
    assert struct == expected_struct