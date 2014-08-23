# coding: utf-8
import pytest
from jinja2 import nodes

from jinja2schema.config import Config
from jinja2schema.core import parse, infer
from jinja2schema.visitors.stmt import visit_macro
from jinja2schema.exceptions import MergeException
from jinja2schema.model import Dictionary, Scalar, List, Unknown, Tuple, String, Number, Macro


test_config = Config()


def test_macro_visitor_1():
    template = '''
    {% macro input(name, value='', type='text', size=20) -%}
        <input type="{{ type }}" name="{{ name }}" value="{{value|e }}" size="{{ size }}">
        {{ x }}
    {%- endmacro %}
    '''
    ast = parse(template).find(nodes.Macro)

    macroses = {}
    struct = visit_macro(ast, macroses, test_config)

    expected_macro = Macro('input', [
        ('name', Unknown(label='argument #1', linenos=[2])),  # must be a scalar
    ], [
        ('value', String(label='argument #2', linenos=[2])),
        ('type', String(label='argument #3', linenos=[2])),
        ('size', Number(label='argument #4', linenos=[2])),
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
        visit_macro(ast, macroses, test_config)

    assert str(e.value) == ('variable "argument #2" (used as string on lines 2) conflicts with '
                            'variable "value" (used as dictionary on lines: 3)')


def test_macro_call_1():
    template = '''
    {% macro format_hello(name, n, m='test', o='test') -%}
        Hello, {{ name }}!
        {{ n }}
    {%- endmacro %}

    {{ format_hello('Anton', 2, 'value', 'value') }}
    {{ format_hello(name='Anton', n=2, m='value', o='value') }}
    {{ format_hello('Anton', n=2, m='value', o='value') }}
    {{ format_hello(name, 2, m='value', o='value') }}
    '''
    struct = infer(template, test_config)
    assert struct == Dictionary({
        'name': Unknown(label='name', linenos=[10])  # TODO must be a scalar
    })


def test_macro_call_2():
    # TODO must fail, name is not a dict
    template = '''
    {% macro format_hello(name, n, m='test', o='test') -%}
        Hello, {{ name }}!
        {{ n }}
    {%- endmacro %}

    {{ format_hello({}, 2, 'value', 'value') }}
    '''
    struct = infer(template, test_config)
    assert struct == Dictionary()


def test_macro_call_3():
    # TODO
    template = '''
    {% macro format_hello(name, n, m='test', o='test') -%}
        Hello, {{ name }}!
        {{ n }}
    {%- endmacro %}

    {{ format_hello(a, 2, 'value', {}) }}
    '''
    with pytest.raises(MergeException):
        infer(template, test_config)
