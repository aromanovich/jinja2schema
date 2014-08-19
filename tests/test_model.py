# coding: utf-8
from jinja2schema.model import Dictionary, Scalar, List, Unknown, Tuple, Number, Boolean, String


def test_to_json_schema():
    struct = Dictionary({
        'list': List(
            Tuple((
                Dictionary({
                    'field': Scalar(label='field', linenos=[3]),
                }, label='a', linenos=[3]),
                Scalar(label='b', linenos=[4])
            ), linenos=[2]),
            label='list', linenos=[2]
        ),
        'x': Unknown(may_be_defined=True),
        'number_var': Number(),
        'string_var': String(),
        'boolean_var': Boolean(),
    })
    scalar_anyof = [
        {'type': 'boolean'},
        {'type': 'null'},
        {'type': 'number'},
        {'type': 'string'},
    ]
    unknown_anyof = [
        {'type': 'object'},
        {'type': 'array'},
        {'type': 'string'},
        {'type': 'number'},
        {'type': 'boolean'},
        {'type': 'null'},
    ]

    json_schema = struct.to_json_schema()
    assert json_schema['type'] == 'object'
    assert set(json_schema['required']) == set(['string_var', 'list', 'boolean_var', 'number_var'])
    assert json_schema['properties'] == {
        'list': {
            'title': 'list',
            'type': 'array',
            'items': {
                'type': 'array',
                'items': [{
                    'title': 'a',
                    'type': 'object',
                    'required': ['field'],
                    'properties': {
                        'field': {
                            'anyOf': scalar_anyof,
                            'title': 'field'
                        }
                    },
                }, {
                    'title': 'b',
                    'anyOf': scalar_anyof,
                }],
            },
        },
        'x': {
            'anyOf': unknown_anyof,
        },
        'number_var': {
            'type': 'number',
        },
        'string_var': {
            'type': 'string',
        },
        'boolean_var': {
            'type': 'boolean',
        },
    }
