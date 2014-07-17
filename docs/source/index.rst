jinja2schema
============

Release v\ |version|.

Introduction
------------

jinja2schema is a library for inferring types from `Jinja2`_ templates.

One of the possible usages of jinja2schema is to create a JSON schema of a context expected by the template
and then use it to render a form (using such JS libraries as `Alpaca`_ or `JSON Editor`_) or to validate
user input.

The library is in an early stage of development. Although the code is extensively tested,
please be prepared for bugs and if you find some, let the author know by `opening a ticket`_.

Examples
--------

Let's get started by inferring types from some expressions.

    >>> from jinja2schema import infer
    >>> infer('{{ x }}')
    {'x': <scalar>}
    >>> infer('{{ x.a.b }}')
    {'x': {'a': {'b': <scalar>}}}
    >>> infer('{{ x.a.b|first }}')
    {'x': {'a': {'b': [<scalar>]}}}
    >>> infer('{{ (x.a.b|first).name }}')
    {'x': {'a': {'b': [{'name': <scalar>}]}}

jinja2schema supports all the flow control structures...

    >>> infer('''
    ... {% for row in items|batch(3, '&nbsp;') %}
    ...     {% for column in row %}
    ...         {% if column.has_title %}
    ...             {{ column.title }}
    ...         {% else %}
    ...             {{ column.desc|truncate(10) }}
    ...         {% endif %}
    ...     {% endfor %}
    ... {% endfor %}
    ... ''')
    {'items': [{'desc': <scalar>, 'has_title': <unknown>, 'title': <scalar>}]}

...and doesn't get confused by scopes.

    >>> s = infer('''
    ... {% for x in xs %}
    ...     {% for x in ys %}
    ...         {{ x.a }}
    ...     {% endfor %}
    ...     {{ x.b }}
    ... {% endfor %}
    ... ''')
    >>> s
    {'xs': [{'b': <scalar>}], 'ys': [{'a': <scalar>}]}

As it was said before, any structure can be converted to `JSON schema`_.

    >>> schema = infer('{% for x in xs %}{{ x }}{% endfor %}').to_json_schema()
    >>> print json.dumps(schema, indent=2)
    {
      "type": "object",
      "properties": {
        "xs": {
          "type": "array",
          "title": "xs",
          "items": {
            "title": "x",
            "anyOf": [
              {"type": "string"},
              {"type": "number"},
              {"type": "boolean"},
              {"type": "null"}
            ]
          }
        }
      },
      "required": ["xs"]
    }

To get a more detailed representation of a structure, one could use :func:`debug_repr`.

    >>> from jinja2schema.util import debug_repr
    >>> print debug_repr(s)
    Dictionary(label=None, required=True, constant=False, linenos=[], {
        xs: List(label=xs, required=True, constant=False, linenos=[2],
                Dictionary(label=x, required=True, constant=False, linenos=[6], {
                    b: Scalar(label=b, required=True, constant=False, linenos=[6])
                })
            )
        ys: List(label=ys, required=True, constant=False, linenos=[3],
                Dictionary(label=x, required=True, constant=False, linenos=[4], {
                    a: Scalar(label=a, required=True, constant=False, linenos=[4])
                })
            )
    })

.. links

.. _opening a ticket: https://github.com/aromanovich/jinja2schema/issues
.. _Jinja2: http://jinja.pocoo.org/docs/
.. _Alpaca: http://www.alpacajs.org/
.. _JSON Editor: https://github.com/jdorn/json-editor
.. _JSON schema: http://json-schema.org/

How It Works
------------

jinja2schema logic based on the following common sense assumptions.

.. note::

    This list is not exhausting and is a subject to change. Probably some of these "axioms" will be customizable
    at some point in the future.

* If ``x`` is printed (``{{ x }}``), ``x`` is a scalar: a string, a number or a boolean;
* If ``x`` is used as an iterable in for loop (``{% for item in x %}``), used with
  a filter that accepts lists (``x|first``), or being indexed with a number (``x[0]``),
  ``x`` is a list;
* If ``x`` is used with a dot (``x.field``) or being indexed with a string (``x['field']``),
  ``x`` is a dictionary.
* A variable can only be used in the one role. So that a list or dictionary can not be printed,
  a string can not be indexed::

    >>> infer('''
    ... {{ x }}
    ... {{ x.name }}
    ... ''')
    jinja2schema.exceptions.MergeException: variable "x" (lines: 2, used as scalar)
    conflicts with variable "x" (lines: 3, used as dictionary)
* Lists are assumed to be homogeneous, meaning all elements of the same list are assumed to
  have the same structure::

    >>> infer('''
    ... {% set xs = [
    ...    1,
    ...    {}
    ... ] %}
    ... ''')
    jinja2schema.exceptions.MergeException: unnamed variable (lines: 3, used as scalar)
    conflicts with unnamed variable (lines: 4, used as dictionary)

Installation
------------

.. code-block:: sh

    $ pip install jinja2schema

API
---

To infer types from a template, simply call :func:`jinja2schema.infer`.

.. autofunction:: jinja2schema.infer

It will return a :class:`.model.Variable` instance, which can be converted to
JSON schema using it's :meth:`.model.Variable.to_json_schema` method.

If you need more than that, please take a look at :ref:`internals`.

.. _internals:

Internals
---------

.. toctree::

    internals

Contributing
------------

The project is hosted on GitHub_.
Please feel free to send a pull request or open an issue.

.. _GitHub: https://github.com/aromanovich/jinja2schema


Running the Tests
~~~~~~~~~~~~~~~~~

.. code-block:: sh

    $ pip install -r ./requirements-dev.txt
    $ ./test.sh
