jinja2schema
============

.. image:: https://travis-ci.org/aromanovich/jinja2schema.svg?branch=master
   :target: https://travis-ci.org/aromanovich/jinja2schema

Demo_ | Documentation_ | GitHub_ |  PyPI_

A library providing heuristic type inference algorithm for `Jinja2`_ templates.

.. code-block:: python

    >>> from jinja2schema import infer, to_json_schema
    >>> s = infer('{{ (x.a.b|first).name }}')
    >>> s
    {'x': {'a': {'b': [{'name': <scalar>}]}}

    >>> s = infer('''
    ... {% for x in xs %}
    ...   {{ x }}
    ... {% endfor %}
    ''')
    >>> s
    {'xs': [<scalar>]}
    >>> to_json_schema(s)
    {
        'type': 'object',
        'required': ['xs'],
        'properties': {
            'xs': {
                'type': 'array'
                'title': 'xs',
                'items': {
                    'title': 'x',
                    'anyOf': [
                        {'type': 'string'},
                        {'type': 'number'},
                        {'type': 'boolean'},
                        {'type': 'null'}
                    ],
                },
            }
        }
    }

More examples can be found at the `demo page`_.

Installing
----------

::

    pip install jinja2schema

License
-------

`BSD license`_

.. _Jinja2: http://jinja.pocoo.org/docs/
.. _Demo: http://jinja2schema.aromanovich.ru/
.. _demo page: http://jinja2schema.aromanovich.ru/
.. _Documentation: http://jinja2schema.rtfd.org/
.. _GitHub: https://github.com/aromanovich/jinja2schema
.. _PyPI: https://pypi.python.org/pypi/jinja2schema
.. _BSD license: https://github.com/aromanovich/jinja2schema/blob/master/LICENSE
