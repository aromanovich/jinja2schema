from jinja2schema.model import Dictionary, Scalar, List, Unknown, Tuple


def test_to_json_schema():
    expected_struct = Dictionary({
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
    })
    scalar_anyof = [
        {'type': 'string'},
        {'type': 'number'},
        {'type': 'boolean'},
        {'type': 'null'},
    ]
    unknown_anyof = [
        {'type': 'object'},
        {'type': 'array'},
        {'type': 'string'},
        {'type': 'number'},
        {'type': 'boolean'},
        {'type': 'null'},
    ]

    assert expected_struct.to_json_schema() == {
        'type': 'object',
        'required': ['list'],
        'properties': {
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
        },
    }
