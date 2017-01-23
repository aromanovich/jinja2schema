jinja2schema
============

.. image:: https://travis-ci.org/aromanovich/jinja2schema.svg?branch=master
    :target: https://travis-ci.org/aromanovich/jinja2schema
    :alt: Build Status

.. image:: https://coveralls.io/repos/aromanovich/jinja2schema/badge.svg?branch=master
    :target: https://coveralls.io/r/aromanovich/jinja2schema?branch=master
    :alt: Coverage

.. image:: http://img.shields.io/pypi/v/jinja2schema.svg
    :target: https://pypi.python.org/pypi/jinja2schema
    :alt: PyPI Version

.. image:: http://img.shields.io/pypi/dm/jinja2schema.svg
    :target: https://pypi.python.org/pypi/jinja2schema
    :alt: PyPI Downloads

Demo_ | Documentation_ | GitHub_ |  PyPI_

A library that provides a heuristic type inference algorithm for `Jinja2`_ templates.

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
.. _Documentation: https://jinja2schema.readthedocs.io/
.. _GitHub: https://github.com/aromanovich/jinja2schema
.. _PyPI: https://pypi.python.org/pypi/jinja2schema
.. _BSD license: https://github.com/aromanovich/jinja2schema/blob/master/LICENSE
