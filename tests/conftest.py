# coding: utf-8
import difflib

from jinja2schema.model import Variable
from jinja2schema.util import _debug_repr


def pytest_assertrepr_compare(op, left, right):
    if isinstance(left, Variable) and isinstance(right, Variable) and op == '==':
        left = _debug_repr(left)
        right = _debug_repr(right)
        return (
            ['comparing two structures'] +
            left +
            ['-' * 45] +
            right +
            ['diff:'] +
            list(difflib.unified_diff(left, right))
        )