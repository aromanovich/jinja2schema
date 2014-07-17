jinja2schema
============

Documentation_ | GitHub_

A library for inferring types from `Jinja2`_ templates.

.. code-block:: python

    >>> from jinja2schema import infer
    >>> infer('{{ (x.a.b|first).name }}')
    {'x': {'a': {'b': [{'name': <scalar>}]}}

    >>> infer('''
    ... {% for x in xs %}
    ...   {{ x }}
    ... {% endfor %}
    ''').to_json_schema()
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


.. _Documentation: http://jinja2schema.rtfd.org/
.. _GitHub: https://github.com/aromanovich/jinja2schema
.. _BSD license: https://github.com/sigmavirus24/uritemplate/blob/master/LICENSE
