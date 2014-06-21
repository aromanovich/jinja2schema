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

    @property
    def required(self):
        return not self.may_be_defined and not self.used_with_default

    def __eq__(self, other):
        return type(self) is type(other)

    def __ne__(self, other):
        return not self.__eq__(other)


class Dictionary(Variable):
    def __init__(self, data=None, **kwargs):
        self.data = data or {}
        super(Dictionary, self).__init__(**kwargs)

    def __eq__(self, other):
        return type(self) is type(other) and self.data == other.data

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
        return (u'Dictionary(required={0.required}, constant={0.constant}, '
                u'linenos={0.linenos}, \n{1}\n)').format(self, data_repr).encode('utf-8')


class List(Variable):
    def __init__(self, el_struct, **kwargs):
        self.el_struct = el_struct
        super(List, self).__init__(**kwargs)

    def __eq__(self, other):
        return type(self) is type(other) and self.el_struct == other.el_struct

    def __repr__(self):
        element_repr = _indent(pprint.pformat(self.el_struct), 2)
        return (u'List(required={0.required}, constant={0.constant}, '
                u'linenos={0.linenos}, \n{1}\n)'.format(self, element_repr).encode('utf-8'))


class Tuple(Variable):
    def __init__(self, el_structs, **kwargs):
        self.el_structs = tuple(el_structs)
        super(Tuple, self).__init__(**kwargs)

    def __eq__(self, other):
        return type(self) is type(other) and self.el_structs == other.el_structs

    def __repr__(self):
        el_structs_repr = _indent(pprint.pformat(self.el_structs), 2)
        return u'Tuple(required={0.required}, linenos={0.linenos} \n{1}\n)'.format(
            self, el_structs_repr).encode('utf-8')


class Scalar(Variable):
    def __repr__(self):
        return (u'Scalar(required={0.required}, constant={0.constant}, '
                u'linenos={0.linenos})').format(self).encode('utf-8')


class Unknown(Variable):
    def __repr__(self):
        return (u'Unknown(required={0.required}, constant={0.constant}, '
                u'linenos={0.linenos})'.format(self).encode('utf-8'))
