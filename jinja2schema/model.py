import pprint


def _indent(s, spaces_num):
    lines = s.split('\n')
    return '\n'.join([spaces_num * ' ' + line for line in lines])


class Variable(object):
    """Base structure class.

    .. attribute:: linenos

        A list of line numbers on which the variable occurs.
    """
    def __init__(self, **kwargs):
        self.linenos = kwargs.pop('linenos', [])
        self.constant = kwargs.pop('constant', False)
        self.may_be_defined = kwargs.pop('may_be_defined', False)
        self.used_with_default = kwargs.pop('used_with_default', False)

    @classmethod
    def _get_kwargs_from_ast(cls, ast):
        return {
            'linenos': [ast.lineno],
        }

    @classmethod
    def from_ast(cls, ast):
        return cls(**cls._get_kwargs_from_ast(ast))

    @property
    def required(self):
        return not self.may_be_defined and not self.used_with_default

    def __eq__(self, other):
        return (
            type(self) is type(other) and
            self.constant == other.constant and
            self.used_with_default == other.used_with_default and
            self.required == other.required and
            self.linenos == other.linenos
        )

    def __ne__(self, other):
        return not self.__eq__(other)


class Dictionary(Variable):
    def __init__(self, data=None, **kwargs):
        self.data = data or {}
        super(Dictionary, self).__init__(**kwargs)

    @classmethod
    def from_ast(cls, ast, data=None):
        return cls(data, **cls._get_kwargs_from_ast(ast))

    def __eq__(self, other):
        return super(Dictionary, self).__eq__(other) and self.data == other.data

    def __setitem__(self, key, value):
        self.data[key] = value

    def __getitem__(self, key):
        return self.data[key]

    def __contains__(self, key):
        return key in self.data

    def __delitem__(self, key):
        del self.data[key]

    def get(self, name, default=None):
        if name in self:
            return self[name]
        else:
            return default

    def items(self):
        return self.data.items()

    def iteritems(self):
        return self.data.iteritems()

    def keys(self):
        return self.data.keys()

    def iterkeys(self):
        return self.data.iterkeys()

    def pop(self, key, default=None):
        return self.data.pop(key, default)

    def __repr__(self):
        data_repr = _indent(pprint.pformat(self.data), 2)
        return u'Dictionary(r={0.required}, c={0.constant}, ls={0.linenos}, \n{1}\n)'.format(
            self, data_repr).encode('utf-8')


class List(Variable):
    def __init__(self, el_struct, **kwargs):
        self.el_struct = el_struct
        super(List, self).__init__(**kwargs)

    @classmethod
    def from_ast(cls, ast, el_struct):
        return cls(el_struct, **cls._get_kwargs_from_ast(ast))

    def __eq__(self, other):
        return super(List, self).__eq__(other) and self.el_struct == other.el_struct

    def __repr__(self):
        element_repr = _indent(pprint.pformat(self.el_struct), 2)
        return u'List(r={0.required}, c={0.constant}, ls={0.linenos}, \n{1}\n)'.format(
            self, element_repr).encode('utf-8')


class Tuple(Variable):
    def __init__(self, el_structs, **kwargs):
        self.el_structs = tuple(el_structs) if el_structs is not None else None
        super(Tuple, self).__init__(**kwargs)

    @classmethod
    def from_ast(cls, ast, el_structs):
        return cls(el_structs, **cls._get_kwargs_from_ast(ast))

    def __eq__(self, other):
        return super(Tuple, self).__eq__(other) and self.el_structs == other.el_structs

    def __repr__(self):
        el_structs_repr = _indent(pprint.pformat(self.el_structs), 2)
        return u'Tuple(r={0.required}, c={0.constant}, ls={0.linenos} \n{1}\n)'.format(
            self, el_structs_repr).encode('utf-8')


class Scalar(Variable):
    def __repr__(self):
        return (u'Scalar(r={0.required}, c={0.constant}, '
                u'ls={0.linenos})').format(self).encode('utf-8')


class Unknown(Variable):
    def __repr__(self):
        return (u'Unknown(r={0.required}, c={0.constant}, '
                u'ls={0.linenos})'.format(self).encode('utf-8'))
