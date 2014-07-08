jinja2schema guesses what context is expected by a template.

It can infer variable structure from expressions:

```python
>>> from jinja2schema import infer
>>> infer('{{ x }}')
{'x': x}
>>> infer('{{ x.a.b }}')
{'x': {'a': {'b': b}}}
>>> infer('{{ x.a.b|first }}')
{'x': {'a': {'b': [<scalar>]}}}
>>> infer('{{ (x.a.b|first).name }}')
{'x': {'a': {'b': [{'name': name}]}}}
```

It can deal with all the flow control structures.

It supports builtin filters:

```python
>>> infer('''
... {% for row in items|batch(3, '&nbsp;') %}
...     {% for column in row %}
...         {{ column.x }}
...     {% endfor %}
... {% endfor %}
... ''')
{'items': [{'x': x}]}
```

```python
>>> infer('''
... {% for number in range(10 - users|length) %}
...     {{ number }}
... {% endfor %}
... ''')
{'users': [<unknown>]}
```

It works correctly with variable scopes:

```python
>>> infer('''
... {% for x in xs %}
...     {% for x in ys %}
...         {{ x.a }}
...     {% endfor %}
...     {{ x.b }}
... {% endfor %}
... ''')
{'xs': [{'b': b}], 'ys': [{'a': a}]}
```

One can use `debug_repr` to see what information is inferred from a template:

```python
>>> s = infer('''
... {% for x in xs %}
...     {{ x.name }}
... {% endfor %}
... {% if y is undefined %}
...     {% set y = 'prefix' ~ a %}
... {% endif %}
... ''')
>>> s
{'a': a, 'xs': [{'name': name}], 'y': y}
>>>
>>> from jinja2schema.util import debug_repr
>>> print debug_repr(s)
Dictionary(label=None, required=True, constant=False, linenos=[], {
    y: Scalar(label=y, required=False, constant=False, linenos=[5, 6])
    xs: List(label=xs, required=True, constant=False, linenos=[2],
            Dictionary(label=x, required=True, constant=False, linenos=[3], {
                name: Scalar(label=name, required=True, constant=False, linenos=[3])
            })
        )
    a: Scalar(label=a, required=True, constant=False, linenos=[6])
})
```

Any template structure can be converted to a JSON schema:

```python
>>> schema = infer('{% for x in xs %}{{ x }}{% endfor %}').to_json_schema()
>>> print json.dumps(schema, indent=2)
{
  "required": [
    "xs"
  ],
  "type": "object",
  "properties": {
    "xs": {
      "items": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "number"
          },
          {
            "type": "boolean"
          },
          {
            "type": "null"
          }
        ],
        "title": "x"
      },
      "type": "array",
      "title": "xs"
    }
  }
}
```

It works based on the following assumptions:

1. If x is printed (``{{ x }}``), x is a scalar: a string, a number or a boolean;
2. If x is used as an iterable in for loop (``{% for item in x %}``), used with
   a filter that accepts lists (``x|first``), or being indexed with a number (``x[0]``),
   x is a list;
3. If x is used with a dot (``x.field``) or being indexed with a string (``x['field']``),
   x is a dictionary.

Notes:

* Variable can only be used in the one role. I.e., a list or dictionary can not be printed,
  a string can not be indexed.
* Lists must be homogeneous, meaning all elements of the same list must have the same type.
