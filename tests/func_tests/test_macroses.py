# coding: utf-8
import pytest
from jinja2 import nodes

from jinja2schema.core import parse, infer
from jinja2schema.visitors.stmt import visit_macro
from jinja2schema.exceptions import MergeException, InvalidExpression
from jinja2schema.model import Dictionary, Scalar, String, Number, Boolean
from jinja2schema.macro import Macro


def test_macro_visitor_1():
    template = '''
    {% macro input(name, value='', type='text', size=20) -%}
        <input type="{{ type }}" name="{{ name }}" value="{{value|e }}" size="{{ size }}">
        {{ x }}
    {%- endmacro %}
    '''
    ast = parse(template).find(nodes.Macro)

    macroses = {}
    struct = visit_macro(ast, macroses)

    expected_macro = Macro('input', [
        ('name', Scalar(label='argument #1', linenos=[2])),
    ], [
        ('value', String(label='argument "value"', linenos=[2])),
        ('type', String(label='argument "type"', linenos=[2])),
        ('size', Number(label='argument "size"', linenos=[2])),
    ])
    macro = macroses['input']
    assert macro.name == expected_macro.name
    assert macro.args == expected_macro.args
    assert macro.kwargs == expected_macro.kwargs

    expected_struct = Dictionary({
        'x': Scalar(label='x', linenos=[4])
    })
    assert struct == expected_struct


def test_macro_visitor_2():
    template = '''
    {% macro input(name, value='') -%}
        {{ value.x }}
    {%- endmacro %}
    '''
    ast = parse(template).find(nodes.Macro)

    macroses = {}
    with pytest.raises(MergeException) as e:
        visit_macro(ast, macroses)

    assert str(e.value) == ('variable "argument "value"" (used as string on lines 2) conflicts with '
                            'variable "value" (used as dictionary on lines: 3)')


def test_macro_call_1():
    template = '''
    {% macro format_hello(name, n, m='test', o='test', dict_arg={'field': 123}) -%}
        Hello, {{ name }}!
        {{ n }}
        {{ dict_arg.field }}
    {%- endmacro %}

    {{ format_hello('Anton', 2, 'value', 'value') }}
    {{ format_hello(name='Anton', n=2, m='value', o='value') }}
    {{ format_hello('Anton', n=2, m='value', o='value') }}
    {{ format_hello(name, 2, m='value', o='value') }}
    {{ format_hello(name, 2, m='value', o='value', dict_arg=d) }}
    '''
    struct = infer(template)
    assert struct == Dictionary({
        'name': Scalar(label='name', linenos=[2, 11, 12]),
        'd': Dictionary(label='d', linenos=[2, 12]),
    })


def test_macro_call_2():
    template = '''
    {% macro user(login, name, is_active=True) %}
        {{ login }} {{ name.first }} {{ name.last }} {{ is_active }}
    {% endmacro %}
    {{ user(data.login, data.name, is_active=data.is_active) }}
    '''
    struct = infer(template)
    assert struct['data'] == Dictionary({
        'login': Scalar(label='login', linenos=[2, 5]),
        'is_active': Boolean(label='is_active', linenos=[2, 5]),
        'name': Dictionary({
            'first': Scalar(label='first', linenos=[3]),
            'last': Scalar(label='last', linenos=[3]),
        }, label='name', linenos=[2, 5]),
    }, label='data', linenos=[5])


def test_macro_call_3():
    template = '''
    {% macro format_hello(name, n, m='test', o='test') -%}
        Hello, {{ name }}!
        {{ n }}
    {%- endmacro %}

    {{ format_hello({}, 2, 'value', 'value') }}
    '''
    with pytest.raises(MergeException) as e:
        infer(template)
    assert str(e.value) == ('unnamed variable (used as dictionary on lines 7) conflicts with '
                            'variable "argument #1" (used as scalar on lines: 2)')

    template = '''
    {% macro format_hello(name, n, m='test', o='test') -%}
        Hello, {{ name }}!
        {{ n }}
    {%- endmacro %}

    {{ format_hello(a, 2, 'value', {}) }}
    '''
    with pytest.raises(MergeException) as e:
        infer(template)
    assert str(e.value) == ('unnamed variable (used as dictionary on lines 7) conflicts with '
                            'variable "argument "o"" (used as string on lines: 2)')


def test_macro_wrong_args():
    macro_template = '''
    {% macro format_hello(name, n, m='test', o='test') -%}
        Hello, {{ name }}!
        {{ n }}
    {%- endmacro %}
    '''

    template = macro_template + '{{ format_hello() }}'
    with pytest.raises(InvalidExpression) as e:
        infer(template)
    assert str(e.value) == 'line 6: incorrect usage of "format_hello". it takes exactly 2 positional arguments'

    template = macro_template + '{{ format_hello(1, 2, "test", "test", 5) }}'
    with pytest.raises(InvalidExpression) as e:
        infer(template)
    assert str(e.value) == 'line 6: incorrect usage of "format_hello". it takes exactly 2 positional arguments'

    template = macro_template + '{{ format_hello(1, 2, missing=123) }}'
    with pytest.raises(InvalidExpression) as e:
        infer(template)
    assert str(e.value) == 'line 6: incorrect usage of "format_hello". unknown keyword argument "missing" is passed'
