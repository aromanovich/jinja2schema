# coding: utf-8
"""
jinja2schema.mergers
~~~~~~~~~~~~~~~~~~~~
"""
import itertools
from jinja2schema.util import debug_repr

from .model import Scalar, Dictionary, List, Unknown, Tuple
from .exceptions import MergeException
from ._compat import zip_longest


def merge(fst, snd, custom_merger=None):
    """Merges two variables.

    :param fst: first variable
    :type fst: :class:`.model.Variable`
    :param snd: second variable
    :type snd: :class:`.model.Variable`

    .. note::

        ``fst`` must reflect expressions that occur in template **before** the expressions of ``snd``.
    """

    # useful for debugging:
    #
    # assert (not (fst.linenos and snd.linenos) or
    #         (fst.linenos == snd.linenos) or  # TODO this is a hack
    #         max(fst.linenos) <= min(snd.linenos))

    if isinstance(fst, Unknown):
        result = snd.clone()
    elif isinstance(snd, Unknown):
        result = fst.clone()
    elif isinstance(fst, Scalar) and isinstance(snd, Scalar):
        fst_type = type(fst)
        snd_type = type(snd)
        if issubclass(fst_type, snd_type):
            result = fst_type()
        elif issubclass(snd_type, fst_type):
            result = snd_type()
        else:
            raise MergeException(fst, snd)
    elif isinstance(fst, Dictionary) and isinstance(snd, Dictionary):
        result = Dictionary()
        for k in set(itertools.chain(fst.iterkeys(), snd.iterkeys())):
            if k in fst and k in snd:
                result[k] = merge(fst[k], snd[k], custom_merger=custom_merger)
            elif k in fst:
                result[k] = fst[k].clone()
            elif k in snd:
                result[k] = snd[k].clone()
    elif isinstance(fst, List) and isinstance(snd, List):
        result = List(merge(fst.item, snd.item, custom_merger=custom_merger))
    elif isinstance(fst, Tuple) and isinstance(snd, Tuple):
        if fst.items is snd.items is None:
            result = Tuple(None)
        else:
            if len(fst.items) != len(snd.items) and not (fst.may_be_extended or snd.may_be_extended):
                raise MergeException(fst, snd)
            result = Tuple([merge(a, b, custom_merger=custom_merger)
                            for a, b in zip_longest(fst.items, snd.items, fillvalue=Unknown())])
    else:
        raise MergeException(fst, snd)
    result.label = fst.label or snd.label
    result.linenos = list(sorted(set(fst.linenos + snd.linenos)))
    result.constant = fst.constant
    result.may_be_defined = fst.may_be_defined
    result.used_with_default = fst.used_with_default and snd.used_with_default
    result.checked_as_defined = fst.checked_as_defined and snd.checked_as_defined
    result.checked_as_undefined = fst.checked_as_undefined and snd.checked_as_undefined
    if fst.value == snd.value:
        result.value = fst.value
    if callable(custom_merger):
        result = custom_merger(fst, snd, result)
    return result


def merge_many(fst, snd, *args):
    struct = merge(fst, snd)
    if args:
        return merge_many(struct, *args)
    else:
        return struct


def merge_bool_expr_structs(fst, snd, operator=None):
    def merger(fst, snd, result):
        result.checked_as_defined = fst.checked_as_defined
        result.checked_as_undefined = fst.checked_as_undefined and snd.checked_as_undefined
        return result
    return merge(fst, snd, custom_merger=merger)


def merge_rtypes(fst, snd, operator=None):
    if operator in ('+', '-'):
        if type(fst) is not type(snd) and not (isinstance(fst, Unknown) or isinstance(snd, Unknown)):
            raise MergeException(fst, snd)
    return merge(fst, snd)
