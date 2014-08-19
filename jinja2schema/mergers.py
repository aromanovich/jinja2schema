# coding: utf-8
"""
jinja2schema.mergers
~~~~~~~~~~~~~~~~~~~~
"""
import itertools

from .model import Scalar, Dictionary, List, Unknown, Tuple
from .exceptions import MergeException


def merge(fst, snd):
    """Merges two variables.

    :param fst: first variable
    :type fst: :class:`.model.Variable`
    :param snd: second variable
    :type snd: :class:`.model.Variable`

    .. note::

        ``fst`` must reflect expressions that occur in template **before** the expressions of ``snd``.
    """
    assert (not (fst.linenos and snd.linenos) or
            max(fst.linenos) <= min(snd.linenos))

    if isinstance(fst, Unknown):
        result = snd
    elif isinstance(snd, Unknown):
        result = fst
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
                result[k] = merge(fst[k], snd[k])
            elif k in fst:
                result[k] = fst[k]
            elif k in snd:
                result[k] = snd[k]
    elif isinstance(fst, List) and isinstance(snd, List):
        result = List(merge(fst.item, snd.item))
    elif isinstance(fst, Tuple) and isinstance(snd, Tuple):
        if fst.items is snd.items is None:
            result = Tuple(None)
        else:
            if len(fst.items) != len(snd.items):
                raise MergeException(fst, snd)
            result = Tuple([merge(a, b) for a, b in zip(fst.items, snd.items)])
    else:
        raise MergeException(fst, snd)
    result.label = fst.label or snd.label
    result.linenos = list(sorted(set(fst.linenos + snd.linenos)))
    result.constant = fst.constant
    result.may_be_defined = fst.may_be_defined
    result.used_with_default = fst.used_with_default and snd.used_with_default
    return result


def merge_rtypes(fst, snd, operator=None):
    if operator in ('+', '-'):
        if type(fst) is not type(snd) and not (isinstance(fst, Unknown) or isinstance(snd, Unknown)):
            raise MergeException(fst, snd)
    return merge(fst, snd)