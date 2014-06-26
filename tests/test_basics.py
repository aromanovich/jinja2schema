import pytest

from jinja2schema.core import infer, parse, MergeException
from jinja2schema.model import List, Dictionary, Scalar, Unknown
from .util import assert_structures_equal


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
        'x': Scalar(linenos=[2, 3, 5], constant=False, may_be_defined=True),
        'y': Scalar(linenos=[7, 10, 12], constant=False, may_be_defined=True),
    })
    assert_structures_equal(struct, expected_struct)

    template = '''
    {{ x }}
    {% if x is undefined %}
        {% set x = 'atata' %}
    {% endif %}
    {{ x }}
    '''
    struct = infer(parse(template))
    expected_struct = Dictionary({
        'x': Scalar(linenos=[2, 3, 4, 6], constant=False, may_be_defined=False),
    })
    assert_structures_equal(struct, expected_struct)


def test_basics_1():
    template = '''
    {% set d = {'x': 123, a: z.qwerty} %}
    {{ d.x }}
    '''
    struct = infer(parse(template))
    expected_struct = Dictionary({
        'a': Scalar(linenos=[2]),
        'z': Dictionary(data={
            'qwerty': Unknown(linenos=[2]),
        }, linenos=[2]),
    })
    assert_structures_equal(struct, expected_struct)

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
        'a': Scalar(linenos=[4, 6]),
        'test1': Unknown(linenos=[2]),
        'test2': Unknown(linenos=[3]),
        'z': Dictionary(data={
            'qwerty': Unknown(linenos=[4]),
            'gsom': Scalar(linenos=[6, 12]),
        }, linenos=[4, 6, 12]),
    })
    assert_structures_equal(struct, expected_struct)


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
        'x': Scalar(linenos=[2, 3, 5, 7]),
    })
    assert_structures_equal(struct, expected_struct)

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
        'z': Unknown(linenos=[2]),
    })
    assert_structures_equal(struct, expected_struct)


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
        'configuration': Scalar(may_be_defined=True, constant=False, linenos=[6]),
        'queue': Scalar(may_be_defined=True, constant=False, linenos=[9]),
        'timestamp': Scalar(constant=False, linenos=[7])
    })
    assert_structures_equal(struct, expected_struct)


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
            'x': Scalar(linenos=[4])
        }, linenos=[4])),
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)


def test_basics_6():
    template = '''
    {% for row in items|batch(3, '&nbsp;') %}
    {% endfor %}
    '''
    struct = infer(parse(template))
    expected_struct = Dictionary({
        'items': List(Unknown()),
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)


def test_basics_7():
    template = '''
    {% for row in items|batch(3, '&nbsp;')|batch(1) %}
        {{ row[1][1].name }}
    {% endfor %}
    '''
    struct = infer(parse(template))
    expected_struct = Dictionary({
        'items': List(Dictionary({
            'name': Scalar(),
        })),
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)



def test_basics_8():
    template = '''
    {% for row in items|batch(3, '&nbsp;')|batch(1) %}
        {{ row[1].name }}
    {% endfor %}
    '''
    with pytest.raises(MergeException):
        infer(parse(template))


def test_basics_9():
    template = '''
    {% set xs = items|batch(3, '&nbsp;') %}
    {{ xs[0][0] }}
    '''
    struct = infer(parse(template))
    expected_struct = Dictionary({
        'items': List(Unknown()),  # TODO it should be Scalar
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)


def test_basics_10():
    template = '''
    {% set items = data|dictsort %}
    {% for x, y in items %}
    {% endfor %}
    '''
    struct = infer(parse(template))
    expected_struct = Dictionary({
        'data': Dictionary({
        }),
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)


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
            'attr1': List(Scalar()),
            'attr2': List(Scalar(), used_with_default=True),
            'attr3': Scalar(used_with_default=True)
        }),
        'xs': List(
            Scalar()  # TODO it should be Dictionary({'is_active': Unknown()})
        ),
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)


def test_basics_12():
    template = '''
    {% for k, v in data|dictsort %}
        {{ k }}
        {{ v }}
    {% endfor %}
    '''
    struct = infer(parse(template))
    expected_struct = Dictionary({
        'data': Dictionary({
        }),
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)


def test_basics_13():  # test dictsort
    template = '''
    {% for k, v in data|dictsort %}
        {{ k.x }}
        {{ v }}
    {% endfor %}
    '''
    with pytest.raises(MergeException):
        infer(parse(template))


def test_raw_1():
    template = '''
    {% raw %}
        {{ x }}
    {% endraw %}
    '''
    struct = infer(parse(template))
    expected_struct = Dictionary()
    assert_structures_equal(struct, expected_struct)


def test_call_range():
    template = '''
    {% for number in range(10 - users|length) %}
        {{ number }}
    {% endfor %}
    '''
    struct = infer(parse(template))
    expected_struct = Dictionary({
        'users': List(Unknown()),
    })
    assert_structures_equal(struct, expected_struct)

    template = '''
    {% for number in range(10 - users|length) %}
        {{ number.field }}
    {% endfor %}
    '''
    with pytest.raises(MergeException):
        infer(parse(template))

    template = '{{ range(10 - users|length) }}'
    with pytest.raises(MergeException):
        infer(parse(template))


def test_call_lipsum():
    template = '''
    {{ lipsum(n=a.field) }}
    '''
    struct = infer(parse(template))
    expected_struct = Dictionary({
        'a': Dictionary({
            'field': Scalar(),
        }),
    })
    assert_structures_equal(struct, expected_struct, check_linenos=False)

    template = '''
    {% for number in lipsum(n=10) %}
    {% endfor %}
    '''
    with pytest.raises(MergeException):
        infer(parse(template))

    template = '{{ lipsum(n=10).field }}'
    with pytest.raises(MergeException):
        infer(parse(template))
