jinja2schema
============

.. image:: https://travis-ci.org/aromanovich/jinja2schema.svg?branch=master
   :target: https://travis-ci.org/aromanovich/jinja2schema

Documentation_ | GitHub_ |  PyPI_

A library for inferring types from `Jinja2`_ templates.

.. code-block:: python

    >>> from jinja2schema import infer
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
    >>> s.to_json_schema()
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

Installing
----------

::

    pip install jinja2schema

License
-------

`BSD license`_

.. _Jinja2: http://jinja.pocoo.org/docs/
.. _Documentation: http://jinja2schema.rtfd.org/
.. _GitHub: https://github.com/aromanovich/jinja2schema
.. _PyPI: https://pypi.python.org/pypi/jinja2schema
.. _BSD license: https://github.com/aromanovich/jinja2schema/blob/master/LICENSE
