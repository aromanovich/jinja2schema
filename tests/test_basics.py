import pytest
from jinja2 import nodes

from jinja2schema.core import infer, parse, MergeException, UnexpectedExpression
from jinja2schema.model import List, Dictionary, Scalar, Unknown


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
    struct = infer(parse(template))
    expected_struct = Dictionary({
        'x': Scalar(linenos=[2, 3, 5], label='x', constant=False, may_be_defined=True),
        'y': Scalar(linenos=[7, 10, 12], label='y', constant=False, may_be_defined=True),
    })
    assert struct == expected_struct

    template = '''
    {{ x }}
    {% if x is undefined %}
        {% set x = 'atata' %}
    {% endif %}
    {{ x }}
    '''
    struct = infer(parse(template))
    expected_struct = Dictionary({
        'x': Scalar(linenos=[2, 3, 4, 6], label='x', constant=False, may_be_defined=False),
    })
    assert struct == expected_struct


def test_basics_1():
    template = '''
    {% set d = {'x': 123, a: z.qwerty} %}
    {{ d.x }}
    '''
    struct = infer(parse(template))
    expected_struct = Dictionary({
        'a': Scalar(label='a', linenos=[2]),
        'z': Dictionary(label='z', data={
            'qwerty': Unknown(label='qwerty', linenos=[2]),
        }, linenos=[2]),
    })
    assert struct == expected_struct

    template = '''
    {% set d = {'x': 123, a: z.qwerty} %}
    {{ d.x.field }}
    '''
    with pytest.raises(MergeException):
        infer(parse(template))

    template = '''
    {% set x = '123' %}
    {{ x.test }}
    '''
    with pytest.raises(MergeException):
        infer(parse(template))

    template = '''
    {% set a = {'x': 123} %}
    {% set b = {a: 'test'} %}
    '''
    with pytest.raises(MergeException):
        infer(parse(template))


def test_basics_2():
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
    struct = infer(parse(template))
    expected_struct = Dictionary({
        'a': Scalar(label='a', linenos=[4, 6]),
        'test1': Unknown(label='test1', linenos=[2]),
        'test2': Unknown(label='test2', linenos=[3]),
        'z': Dictionary(data={
            'qwerty': Unknown(label='qwerty', linenos=[4]),
            'gsom': Scalar(label='gsom', linenos=[6, 12]),
        }, label='z', linenos=[4, 6, 12]),
    })
    assert struct == expected_struct


def test_basics_3():
    template = '''
    {% if x %}
        {% set x = '123' %}
    {% else %}
        {% set x = '456' %}
    {% endif %}
    {{ x }}
    '''
    struct = infer(parse(template))
    expected_struct = Dictionary({
        'x': Scalar(label='x', linenos=[2, 3, 5, 7]),
    })
    assert struct == expected_struct

    template = '''
    {% if z %}
        {% set x = '123' %}
    {% else %}
        {% set x = '456' %}
    {% endif %}
    {{ x }}
    '''
    struct = infer(parse(template))
    expected_struct = Dictionary({
        'z': Unknown(label='z', linenos=[2]),
    })
    assert struct == expected_struct


def test_basics_4():
    template = '''
    {% set xys = [
        ('a', 0.3),
        ('b', 0.3),
    ] %}
    {% if configuration is undefined %}
        {% set configuration = 'prefix-' ~ timestamp %}
    {% endif %}
    queue: {{ queue if queue is defined else 'wizard' }}
    description: >-
    {% for x, y in xys %}
        {{ loop.index }}:
        {{ x }} {{ y }}
    {% endfor %}
    '''
    struct = infer(parse(template))
    expected_struct = Dictionary({
        'configuration': Scalar(label='configuration', may_be_defined=True, constant=False, linenos=[6, 7]),
        'queue': Scalar(label='queue', may_be_defined=True, constant=False, linenos=[9]),
        'timestamp': Scalar(label='timestamp', constant=False, linenos=[7])
    })
    assert struct == expected_struct


def test_basics_5():
    template = '''
    {% for row in items|batch(3, '&nbsp;') %}
        {% for column in row %}
            {{ column.x }}
        {% endfor %}
    {% endfor %}
    '''
    struct = infer(parse(template))
    expected_struct = Dictionary({
        'items': List(Dictionary({
            'x': Scalar(label='x', linenos=[4])
        }, label='column', linenos=[4]), label='items', linenos=[2, 3]),
    })
    assert struct == expected_struct


def test_basics_6():
    template = '''
    {% for row in items|batch(3, '&nbsp;') %}
    {% endfor %}
    '''
    struct = infer(parse(template))
    expected_struct = Dictionary({
        'items': List(Unknown(), label='items', linenos=[2]),
    })
    assert struct == expected_struct


def test_basics_7():
    template = '''
    {% for row in items|batch(3, '&nbsp;')|batch(1) %}
        {{ row[1][1].name }}
    {% endfor %}
    '''
    struct = infer(parse(template))
    expected_struct = Dictionary({
        'items': List(Dictionary({
            'name': Scalar(label='name', linenos=[3]),
        }, linenos=[3]), label='items', linenos=[2, 3]),
    })
    assert struct == expected_struct


def test_basics_8():
    template = '''
    {% for row in items|batch(3, '&nbsp;')|batch(1) %}
        {{ row[1].name }}
    {% endfor %}
    '''
    with pytest.raises(UnexpectedExpression) as excinfo:
        infer(parse(template))
    e = excinfo.value

    assert isinstance(e.actual_ast, nodes.Filter)
    assert e.expected_struct == List(
        Dictionary({
            'name': Scalar(label='name', constant=False, linenos=[3])
        }, constant=False, linenos=[3]),
        label='row', constant=False, linenos=[2, 3]
    )
    assert e.actual_struct == List(List(Unknown()))


def test_basics_9():
    template = '''
    {% set xs = items|batch(3, '&nbsp;') %}
    {{ xs[0][0] }}
    '''
    struct = infer(parse(template))
    expected_struct = Dictionary({
        'items': List(Unknown(), label='items', linenos=[2]),  # TODO it should be Scalar
    })
    assert struct == expected_struct


def test_basics_10():
    template = '''
    {% set items = data|dictsort %}
    {% for x, y in items %}
    {% endfor %}
    '''
    struct = infer(parse(template))
    expected_struct = Dictionary({
        'data': Dictionary({}, label='data', linenos=[2]),
    })
    assert struct == expected_struct


def test_basics_11():
    template = '''
    {{ a|xmlattr }}
    {{ a.attr1|join(',') }}
    {{ a.attr2|default([])|first }}
    {{ a.attr3|default('gsom') }}
    {% for x in xs|rejectattr('is_active') %}
        {{ x }}
    {% endfor %}
    '''
    struct = infer(parse(template))
    expected_struct = Dictionary({
        'a': Dictionary({
            'attr1': List(Scalar(), label='attr1', linenos=[3]),
            'attr2': List(Scalar(linenos=[4]), label='attr2', linenos=[4], used_with_default=True),
            'attr3': Scalar(label='attr3', linenos=[5], used_with_default=True)
        }, label='a', linenos=[2, 3, 4, 5]),
        'xs': List(
            Scalar(label='x', linenos=[7]),  # TODO it should be Dictionary({'is_active': Unknown()})
            label='xs',
            linenos=[6]
        ),
    })
    assert struct == expected_struct


def test_basics_12():
    template = '''
    {% for k, v in data|dictsort %}
        {{ k }}
        {{ v }}
    {% endfor %}
    '''
    struct = infer(parse(template))
    expected_struct = Dictionary({
        'data': Dictionary({}, label='data', linenos=[2]),
    })
    assert struct == expected_struct


def test_basics_13():  # test dictsort
    template = '''
    {% for k, v in data|dictsort %}
        {{ k.x }}
        {{ v }}
    {% endfor %}
    '''
    with pytest.raises(UnexpectedExpression):
        infer(parse(template))


def test_raw_1():
    template = '''
    {% raw %}
        {{ x }}
    {% endraw %}
    '''
    struct = infer(parse(template))
    expected_struct = Dictionary()
    assert struct == expected_struct


def test_call_range():
    template = '''
    {% for number in range(10 - users|length) %}
        {{ number }}
    {% endfor %}
    '''
    struct = infer(parse(template))
    expected_struct = Dictionary({
        'users': List(Unknown(), label='users', linenos=[2]),
    })
    assert struct == expected_struct

    template = '''
    {% for number in range(10 - users|length) %}
        {{ number.field }}
    {% endfor %}
    '''
    with pytest.raises(MergeException):
        infer(parse(template))

    template = '{{ range(10 - users|length) }}'
    with pytest.raises(UnexpectedExpression):
        infer(parse(template))


def test_call_lipsum():
    template = '''
    {{ lipsum(n=a.field) }}
    '''
    struct = infer(parse(template))
    expected_struct = Dictionary({
        'a': Dictionary({
            'field': Scalar(label='field', linenos=[2]),
        }, label='a', linenos=[2]),
    })
    assert struct == expected_struct

    template = '''
    {% for number in lipsum(n=10) %}
    {% endfor %}
    '''
    with pytest.raises(UnexpectedExpression):
        infer(parse(template))

    template = '{{ lipsum(n=10).field }}'
    with pytest.raises(UnexpectedExpression):
        infer(parse(template))


def test_just_test():
    template = '''
    {% set args = ['foo'] if foo else [] %}
    {% set args = args + ['bar'] %}
    {% set args = args + (['zork'] if zork else []) %}
    f({{args|join(sep)}});
    '''
    struct = infer(parse(template))
    expected_struct = Dictionary({
        'foo': Unknown(label='foo', linenos=[2]),
        'zork': Unknown(label='zork', linenos=[4]),
        'sep': Scalar(label='sep', linenos=[5])
    })
    assert struct == expected_struct
