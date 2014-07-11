jinja2schema
============

Release v\ |version|.

jinja2schema is a library for inferring types from `Jinja2`_ templates.

Examples
--------

Let's try some expressions:

    >>> from jinja2schema import infer
    >>> infer('{{ x }}')
    {'x': <scalar>}
    >>> infer('{{ x.a.b }}')
    {'x': {'a': {'b': <scalar>}}}
    >>> infer('{{ x.a.b|first }}')
    {'x': {'a': {'b': [<scalar>]}}}
    >>> infer('{{ (x.a.b|first).name }}')
    {'x': {'a': {'b': [{'name': <scalar>}]}}

Let's add flow control structures and use builtin filters:

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


Any structure can be converted to `JSON schema`_:

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

:func:`debug_repr` shows much more detailed representation of ``s``:

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

.. _Jinja2: http://jinja.pocoo.org/docs/
.. _JSON schema: http://json-schema.org/

Overview
--------
jinja2schema logic based on the following common sense assumptions.

* If ``x`` is printed (``{{ x }}``), ``x`` is a scalar: a string, a number or a boolean;
* If ``x`` is used as an iterable in for loop (``{% for item in x %}``), used with
  a filter that accepts lists (``x|first``), or being indexed with a number (``x[0]``),
  ``x`` is a list;
* If ``x`` is used with a dot (``x.field``) or being indexed with a string (``x['field']``),
  ``x`` is a dictionary.
* A variable can only be used in the one role. So that a list or dictionary can not be printed,
  a string can not be indexed;
* Lists are assumed to be homogeneous, meaning all elements of the same list are assumed to
  have the same structure.

This list is not exhausting and is a subject to change. Probably some of these assumptions will be customizable
at some point in the future.


Modules
-------

.. toctree::
   :maxdepth: 1

   api

Internals
~~~~~~~~~

For objects you're not likely to see in practice. This is useful if you ever
feel the need to contribute to the project.

.. toctree::
   :maxdepth: 1


Installation
------------

.. code-block:: sh

    $ pip install jinja2schema


Contributing
------------


The project is hosted on GitHub_.
Please feel free to send a pull request or open an issue.

.. links
.. _GitHub: https://github.com/aromanovich/jinja2schema


Running the Tests
~~~~~~~~~~~~~~~~~

.. code-block:: sh

    $ pip install -r ./requirements-dev.txt
    $ ./test.sh


.. toctree::

    testing
